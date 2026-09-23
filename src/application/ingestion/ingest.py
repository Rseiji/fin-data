"""Bronze layer ingestion – save raw scraped data to the database."""
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from sqlalchemy.orm import Session

from src.domain.entities.quote import RawQuote
from src.infrastructure.database import repositories
from src.config.settings import settings


def resolve_symbol_lookback_days(db: Session, symbol: str, default_days: int) -> int:
    """Return the lookback window for a symbol based on its latest stored data."""
    latest = repositories.find_latest_quote(db, symbol)
    if latest is None:
        return max(1, default_days)

    now = datetime.now(tz=timezone.utc)
    elapsed = max((now - latest.quote_date).total_seconds(), 0)
    if elapsed <= 0:
        return 1

    days_since = max(1, int(elapsed // 86400) + 1)
    return min(max(1, default_days), days_since)

logger = logging.getLogger(__name__)
LOOKBACK_DAYS = settings.ingestion_lookback_days


def _build_raw_quote(record: Dict[str, Any]) -> RawQuote:
    return RawQuote(
        id=str(uuid.uuid4()),
        symbol=record["symbol"],
        asset_type=record["asset_type"],
        source=record["source"],
        raw_payload=json.dumps(record),
        ingested_at=datetime.now(tz=timezone.utc),
    )


def ingest_records(
    db: Session,
    records: List[Dict[str, Any]],
    *,
    use_batch: bool = False,
    batch_size: int = 500,
) -> int:
    """Persist a list of raw scraped records to the bronze layer.

    By default the function preserves the original per-record save behavior for
    compatibility with existing callers and tests. The ETL pipeline can opt into
    the batch path to reduce SQL round-trips.
    """
    raw_quotes: List[RawQuote] = []
    for record in records:
        try:
            raw_quotes.append(_build_raw_quote(record))
        except Exception as exc:
            logger.error("Failed to ingest record %s: %s", record.get("symbol"), exc)

    saved = 0
    if use_batch and raw_quotes:
        try:
            saved = repositories.save_raw_quotes(db, raw_quotes, batch_size=batch_size)
        except Exception as exc:
            logger.error("Failed to persist %d raw quote records: %s", len(raw_quotes), exc)
            saved = 0
    else:
        for raw in raw_quotes:
            try:
                repositories.save_raw_quote(db, raw)
                saved += 1
            except Exception as exc:
                logger.error("Failed to ingest record %s: %s", raw.symbol, exc)

    logger.info("Ingested %d/%d records", saved, len(records))
    return saved


def run_ingestion_pipeline(db: Session) -> Dict[str, int]:
    """
    Run the full ingestion pipeline for all data sources.

    Returns a dict with ingested counts per source type.
    """
    from src.infrastructure.scrapers import crypto, stocks, indexes, currencies

    stock_assets = repositories.list_enabled_assets(db, "stock")
    etf_assets = repositories.list_enabled_assets(db, "etf")
    crypto_assets = repositories.list_enabled_assets(db, "crypto")
    currency_assets = repositories.list_enabled_assets(db, "currency")
    index_assets = repositories.list_enabled_assets(db, "index")

    stock_lookbacks = {asset.symbol: resolve_symbol_lookback_days(db, asset.symbol, LOOKBACK_DAYS) for asset in stock_assets}
    etf_lookbacks = {asset.symbol: resolve_symbol_lookback_days(db, asset.symbol, LOOKBACK_DAYS) for asset in etf_assets}
    crypto_lookbacks = {asset.symbol: resolve_symbol_lookback_days(db, asset.symbol, LOOKBACK_DAYS) for asset in crypto_assets}
    currency_lookbacks = {asset.symbol: resolve_symbol_lookback_days(db, asset.symbol, LOOKBACK_DAYS) for asset in currency_assets}
    index_lookbacks = {asset.symbol: resolve_symbol_lookback_days(db, asset.symbol, LOOKBACK_DAYS) for asset in index_assets}

    logger.info(
        "Ingestion assets: crypto=%d stocks=%d etfs=%d indexes=%d currencies=%d",
        len(crypto_assets), len(stock_assets), len(etf_assets),
        len(index_assets), len(currency_assets),
    )

    results: Dict[str, int] = {}
    source_jobs: Dict[str, Callable[[], List[Dict[str, Any]]]] = {
        "crypto": lambda: crypto.scrape_crypto_prices(assets=crypto_assets, lookback_days=LOOKBACK_DAYS, lookback_by_symbol=crypto_lookbacks),
        "stocks": lambda: stocks.scrape_stocks(stock_assets, lookback_days=LOOKBACK_DAYS, lookback_by_symbol=stock_lookbacks),
        "etfs": lambda: stocks.scrape_etfs(etf_assets, lookback_days=LOOKBACK_DAYS, lookback_by_symbol=etf_lookbacks),
        "indexes": lambda: indexes.scrape_all_indexes(lookback_days=LOOKBACK_DAYS, assets=index_assets, lookback_by_symbol=index_lookbacks),
        "currencies": lambda: currencies.scrape_currencies(lookback_days=LOOKBACK_DAYS, assets=currency_assets, lookback_by_symbol=currency_lookbacks),
    }

    with ThreadPoolExecutor(max_workers=min(5, len(source_jobs))) as executor:
        future_map = {
            executor.submit(_fetch_source_data, source_name, fetch_fn): source_name
            for source_name, fetch_fn in source_jobs.items()
        }
        for future in future_map:
            source_name = future_map[future]
            try:
                fetched = future.result()
                logger.info("Starting ingestion: %s", source_name)
                started_at = time.monotonic()
                results[source_name] = ingest_records(db, fetched, use_batch=True)
                logger.info(
                    "Completed ingestion: %s fetched=%d persisted=%d duration=%.2fs",
                    source_name, len(fetched), results[source_name], time.monotonic() - started_at,
                )
            except Exception as exc:
                logger.exception("Failed to ingest source %s: %s", source_name, exc)
                results[source_name] = 0

    logger.info("Ingestion complete: %s", results)
    return results


def _fetch_source_data(source_name: str, fetch_fn: Callable[[], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    logger.info("Fetching source data: %s", source_name)
    started_at = time.monotonic()
    fetched = fetch_fn()
    logger.info("Fetched source %s in %.2fs (%d records)", source_name, time.monotonic() - started_at, len(fetched))
    return fetched

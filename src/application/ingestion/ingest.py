"""Bronze layer ingestion – save raw scraped data to the database."""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from src.domain.entities.quote import RawQuote
from src.infrastructure.database import repositories
from src.config.settings import settings

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


def ingest_records(db: Session, records: List[Dict[str, Any]]) -> int:
    """Persist a list of raw scraped records to the bronze layer."""
    saved = 0
    for record in records:
        try:
            raw = _build_raw_quote(record)
            repositories.save_raw_quote(db, raw)
            saved += 1
        except Exception as exc:
            logger.error("Failed to ingest record %s: %s", record.get("symbol"), exc)
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

    results: Dict[str, int] = {}

    logger.info("Starting ingestion: crypto")
    crypto_data = crypto.scrape_crypto_prices(assets=crypto_assets, lookback_days=LOOKBACK_DAYS)
    results["crypto"] = ingest_records(db, crypto_data)

    logger.info("Starting ingestion: stocks")
    stock_data = stocks.scrape_stocks(stock_assets, lookback_days=LOOKBACK_DAYS)
    results["stocks"] = ingest_records(db, stock_data)

    logger.info("Starting ingestion: etfs")
    etf_data = stocks.scrape_etfs(etf_assets, lookback_days=LOOKBACK_DAYS)
    results["etfs"] = ingest_records(db, etf_data)

    logger.info("Starting ingestion: indexes")
    index_data = indexes.scrape_all_indexes(lookback_days=LOOKBACK_DAYS, assets=index_assets)
    results["indexes"] = ingest_records(db, index_data)

    logger.info("Starting ingestion: currencies")
    currency_data = currencies.scrape_currencies(lookback_days=LOOKBACK_DAYS, assets=currency_assets)
    results["currencies"] = ingest_records(db, currency_data)

    return results

"""Load historical data for every enabled non-crypto asset in the catalog.

Usage:
    PYTHONPATH=. python scripts/initial_load_all_assets.py
    PYTHONPATH=. python scripts/initial_load_all_assets.py --days 2190 --reset

The default window is approximately six years. Crypto assets are intentionally
skipped until the CoinGecko integration is stable.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from src.application.aggregation.aggregate import run_aggregation_pipeline
from src.application.ingestion.ingest import ingest_records
from src.application.transformation.transform import run_transformation_pipeline
from src.infrastructure.database import models, repositories
from src.infrastructure.database.engine import SessionLocal, create_all_tables
from src.infrastructure.scrapers import currencies, indexes, stocks


DEFAULT_DAYS = 2190
logger = logging.getLogger(__name__)


def _clear_symbols(db: Session, symbols: Iterable[str]) -> None:
    symbol_list = list(symbols)
    if not symbol_list:
        return
    logger.info("Resetting existing data for %d assets", len(symbol_list))
    for model in (models.GoldDailySummary, models.SilverQuote, models.BronzeQuote):
        db.query(model).filter(model.symbol.in_(symbol_list)).delete(
            synchronize_session=False
        )
    db.commit()
    logger.info("Reset completed")


def _fetch_records(assets: list[models.TrackedAsset], days: int):
    assets_by_type = {
        asset_type: [asset for asset in assets if asset.asset_type.value == asset_type]
        for asset_type in ("stock", "etf", "currency", "index")
    }
    records = []
    scrapers = (
        ("stocks", stocks.scrape_stocks, assets_by_type["stock"]),
        ("ETFs", stocks.scrape_etfs, assets_by_type["etf"]),
        ("currencies", currencies.scrape_currencies, assets_by_type["currency"]),
        ("indexes", indexes.scrape_all_indexes, assets_by_type["index"]),
    )
    for name, scraper, source_assets in scrapers:
        if not source_assets:
            logger.info("Skipping %s: no enabled assets", name)
            continue
        started_at = time.monotonic()
        logger.info(
            "Fetching %s: %d assets, %d days",
            name,
            len(source_assets),
            days,
        )
        if name in ("currencies", "indexes"):
            source_records = scraper(assets=source_assets, lookback_days=days)
        else:
            source_records = scraper(source_assets, lookback_days=days)
        records.extend(source_records)
        logger.info(
            "Fetched %s: %d records in %.1fs",
            name,
            len(source_records),
            time.monotonic() - started_at,
        )
    return records


def run_initial_load_all_assets(days: int = DEFAULT_DAYS, reset: bool = False) -> dict:
    if days <= 0:
        raise ValueError("days must be greater than 0")

    started_at = time.monotonic()
    logger.info("Starting historical load: %d days", days)
    logger.info("Crypto assets are disabled and will be skipped")
    create_all_tables()
    logger.info("Database ready")
    db = SessionLocal()
    try:
        assets = repositories.list_enabled_assets(db)
        logger.info("Found %d enabled assets in tracked_assets", len(assets))
        assets = [asset for asset in assets if asset.asset_type != models.AssetType.crypto]
        symbols = [asset.symbol for asset in assets]
        logger.info("Selected %d non-crypto assets for loading", len(assets))

        if reset:
            _clear_symbols(db, symbols)

        records = _fetch_records(assets, days)
        logger.info("Fetched %d records in total", len(records))
        logger.info("Persisting bronze records")
        bronze = ingest_records(db, records)
        logger.info("Bronze complete: %d records persisted", bronze)
        logger.info("Transforming silver records for %d assets", len(symbols))
        transformed = run_transformation_pipeline(db, symbols)
        logger.info(
            "Silver complete: %d records transformed",
            sum(transformed.values()),
        )
        logger.info("Aggregating gold summaries for %d assets", len(symbols))
        aggregated = run_aggregation_pipeline(db, symbols)
        logger.info(
            "Gold complete: %d daily summaries created",
            sum(aggregated.values()),
        )

        result = {
            "days": days,
            "symbols": symbols,
            "skipped_asset_types": ["crypto"],
            "bronze_records": bronze,
            "transformed": transformed,
            "aggregated": aggregated,
        }
        logger.info(
            "Historical load completed in %.1fs",
            time.monotonic() - started_at,
        )
        return result
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load historical data for all enabled catalog assets"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"Number of past days to fetch (default: {DEFAULT_DAYS})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing bronze/silver/gold rows for catalog symbols first",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    print(run_initial_load_all_assets(days=args.days, reset=args.reset))


if __name__ == "__main__":
    main()
"""Load historical data for every enabled non-crypto asset in the catalog.

Usage:
    PYTHONPATH=. python scripts/initial_load_all_assets.py
    PYTHONPATH=. python scripts/initial_load_all_assets.py --days 2190 --reset

The default window is approximately six years. Crypto assets are intentionally
skipped until the CoinGecko integration is stable.
"""

from __future__ import annotations

import argparse
import sys
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


def _clear_symbols(db: Session, symbols: Iterable[str]) -> None:
    symbol_list = list(symbols)
    if not symbol_list:
        return
    for model in (models.GoldDailySummary, models.SilverQuote, models.BronzeQuote):
        db.query(model).filter(model.symbol.in_(symbol_list)).delete(
            synchronize_session=False
        )
    db.commit()


def _fetch_records(assets: list[models.TrackedAsset], days: int):
    assets_by_type = {
        asset_type: [asset for asset in assets if asset.asset_type.value == asset_type]
        for asset_type in ("stock", "etf", "currency", "index")
    }
    return (
        stocks.scrape_stocks(assets_by_type["stock"], lookback_days=days)
        + stocks.scrape_etfs(assets_by_type["etf"], lookback_days=days)
        + currencies.scrape_currencies(assets=assets_by_type["currency"], lookback_days=days)
        + indexes.scrape_all_indexes(assets=assets_by_type["index"], lookback_days=days)
    )


def run_initial_load_all_assets(days: int = DEFAULT_DAYS, reset: bool = False) -> dict:
    if days <= 0:
        raise ValueError("days must be greater than 0")

    create_all_tables()
    db = SessionLocal()
    try:
        assets = repositories.list_enabled_assets(db)
        assets = [asset for asset in assets if asset.asset_type != models.AssetType.crypto]
        symbols = [asset.symbol for asset in assets]

        if reset:
            _clear_symbols(db, symbols)

        records = _fetch_records(assets, days)
        bronze = ingest_records(db, records)
        transformed = run_transformation_pipeline(db, symbols)
        aggregated = run_aggregation_pipeline(db, symbols)

        return {
            "days": days,
            "symbols": symbols,
            "skipped_asset_types": ["crypto"],
            "bronze_records": bronze,
            "transformed": transformed,
            "aggregated": aggregated,
        }
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
    print(run_initial_load_all_assets(days=args.days, reset=args.reset))


if __name__ == "__main__":
    main()
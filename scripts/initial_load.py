"""Initial historical load for selected symbols and source categories.

Usage examples:
    python scripts/initial_load.py --symbols PETR4 IVVB11 --source stocks --days 2190
    python scripts/initial_load.py --symbols BTCUSD ETHUSD --source crypto --days 365
    python scripts/initial_load.py --symbols PETR4 IVVB11 BTCUSD --source stocks --days 2190
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from src.application.aggregation.aggregate import run_aggregation_pipeline
from src.application.ingestion.ingest import ingest_records
from src.application.transformation.transform import run_transformation_pipeline
from src.infrastructure.database.engine import SessionLocal, create_all_tables, engine
from src.infrastructure.database import models
from src.infrastructure.scrapers.crypto import scrape_crypto_prices
from src.infrastructure.scrapers.currencies import scrape_currencies
from src.infrastructure.scrapers.indexes import scrape_all_indexes
from src.infrastructure.scrapers.stocks import scrape_etfs, scrape_stocks


SOURCE_HANDLERS = {
    "stocks": lambda symbols, days: scrape_stocks(symbols=symbols, lookback_days=days),
    "etfs": lambda symbols, days: scrape_etfs(symbols=symbols, lookback_days=days),
    "crypto": lambda symbols, days: scrape_crypto_prices(symbols=symbols, lookback_days=days),
    "currency": lambda symbols, days: scrape_currencies(symbols=symbols, lookback_days=days),
    "index": lambda symbols, days: scrape_all_indexes(lookback_days=days, symbols=symbols),
}


def _fetch_records(source: str, symbols: List[str], days: int):
    if source not in SOURCE_HANDLERS:
        raise ValueError(
            f"Unsupported source '{source}'. Supported: {', '.join(SOURCE_HANDLERS.keys())}"
        )
    return SOURCE_HANDLERS[source](symbols, days)


def _clear_symbols(db: Session, symbols: Iterable[str]) -> None:
    symbol_list = list(symbols)
    if not symbol_list:
        return
    for model in [models.GoldDailySummary, models.SilverQuote, models.BronzeQuote]:
        db.query(model).filter(model.symbol.in_(symbol_list)).delete(synchronize_session=False)
    db.commit()


def run_initial_load(symbols: List[str], source: str, days: int, reset: bool = False) -> dict:
    """Run a historical load for a given source/category."""
    db = SessionLocal()
    try:
        create_all_tables()

        if reset:
            _clear_symbols(db, symbols)

        records = _fetch_records(source=source, symbols=symbols, days=days)
        bronze_count = ingest_records(db, records)

        transformed = run_transformation_pipeline(db, symbols)
        aggregated = run_aggregation_pipeline(db, symbols)

        return {
            "source": source,
            "symbols": symbols,
            "days": days,
            "bronze_records": bronze_count,
            "transformed": transformed,
            "aggregated": aggregated,
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initial load for historic data by symbol and source")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to load, e.g. PETR4 IVVB11")
    parser.add_argument("--source", required=True, choices=sorted(SOURCE_HANDLERS.keys()), help="Data source scraper category")
    parser.add_argument("--days", type=int, required=True, help="How many past days to fetch")
    parser.add_argument("--reset", action="store_true", help="Delete existing bronze/silver/gold rows for these symbols before loading")
    args = parser.parse_args()

    if args.days <= 0:
        raise ValueError("--days must be greater than 0")

    result = run_initial_load(args.symbols, args.source, args.days, reset=args.reset)
    print(result)


if __name__ == "__main__":
    main()

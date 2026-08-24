"""Execute the medallion ETL pipeline for selected symbols.

Usage:
    python scripts/run_medallion_etl.py PETR4 IVVB11
    python scripts/run_medallion_etl.py --symbols PETR4 IVVB11 --source stocks
"""

from __future__ import annotations

import argparse
from typing import Iterable, List

from src.application.aggregation.aggregate import run_aggregation_pipeline
from src.application.ingestion.ingest import run_ingestion_pipeline
from src.application.transformation.transform import run_transformation_pipeline
from src.infrastructure.database.engine import SessionLocal
from src.infrastructure.scrapers.crypto import CRYPTO_SYMBOLS
from src.infrastructure.scrapers.currencies import CURRENCY_PAIRS
from src.infrastructure.scrapers.indexes import BCB_CODES
from src.infrastructure.scrapers.stocks import ETF_SYMBOLS, STOCK_SYMBOLS


def resolve_all_symbols(symbols: List[str] | None = None) -> List[str]:
    if symbols is not None:
        return [s.upper() for s in symbols]

    return (
        list(STOCK_SYMBOLS)
        + list(ETF_SYMBOLS)
        + list(CRYPTO_SYMBOLS.keys())
        + list(CURRENCY_PAIRS.keys())
        + list(BCB_CODES.keys())
    )


def run_etl(symbols: List[str] | None = None) -> dict:
    db = SessionLocal()
    try:
        target_symbols = resolve_all_symbols(symbols)

        bronze = run_ingestion_pipeline(db)
        silver = run_transformation_pipeline(db, target_symbols)
        gold = run_aggregation_pipeline(db, target_symbols)

        return {
            "symbols": target_symbols,
            "bronze": bronze,
            "silver": silver,
            "gold": gold,
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the project medallion ETL pipeline")
    parser.add_argument("symbols", nargs="*", help="Optional symbol list. If omitted, uses default project list.")
    args = parser.parse_args()

    result = run_etl(args.symbols)
    print(result)


if __name__ == "__main__":
    main()

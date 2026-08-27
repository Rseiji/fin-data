"""Update already-tracked symbols by running the medallion ETL pipeline.

Usage:
    python scripts/update_tracked_assets.py PETR4 IVVB11
    python scripts/update_tracked_assets.py --symbols PETR4 IVVB11 --source stocks
"""

from __future__ import annotations

import argparse
from typing import Iterable, List

from src.application.aggregation.aggregate import run_aggregation_pipeline
from src.application.ingestion.ingest import run_ingestion_pipeline
from src.application.transformation.transform import run_transformation_pipeline
from src.infrastructure.database import repositories
from src.infrastructure.database.engine import SessionLocal, create_all_tables


def resolve_all_symbols(symbols: List[str] | None = None) -> List[str]:
    if symbols:
        return [s.upper() for s in symbols]

    db = SessionLocal()
    try:
        return repositories.list_enabled_symbols(db)
    finally:
        db.close()


def run_etl(symbols: List[str] | None = None) -> dict:
    create_all_tables()
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

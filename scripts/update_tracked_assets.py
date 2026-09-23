"""Update already-tracked symbols by running the medallion ETL pipeline.

Usage:
    python scripts/update_tracked_assets.py PETR4 IVVB11
    python scripts/update_tracked_assets.py --symbols PETR4 IVVB11 --source stocks
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Iterable, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import settings
from src.application.aggregation.aggregate import run_aggregation_pipeline
from src.application.ingestion.ingest import run_ingestion_pipeline
from src.application.transformation.transform import run_transformation_pipeline
from src.infrastructure.database import repositories
from src.infrastructure.database.engine import SessionLocal, create_all_tables

logger = logging.getLogger(__name__)


def resolve_all_symbols(symbols: List[str] | None = None) -> List[str]:
    if symbols:
        return [s.upper() for s in symbols]

    db = SessionLocal()
    try:
        return repositories.list_enabled_symbols(db)
    finally:
        db.close()


def run_etl(symbols: List[str] | None = None) -> dict:
    started_at = time.monotonic()
    logger.info("Starting tracked-assets update")

    stage_started_at = time.monotonic()
    create_all_tables()
    logger.info("Database ready (%.1fs)", time.monotonic() - stage_started_at)
    db = SessionLocal()
    try:
        target_symbols = resolve_all_symbols(symbols)
        logger.info("Updating %d tracked assets", len(target_symbols))

        stage_started_at = time.monotonic()
        logger.info("Starting bronze ingestion")
        bronze = run_ingestion_pipeline(db)
        logger.info("Bronze ingestion complete: %s (%.1fs)", bronze, time.monotonic() - stage_started_at)

        stage_started_at = time.monotonic()
        logger.info("Starting silver transformation")
        silver = run_transformation_pipeline(db, target_symbols)
        logger.info("Silver transformation complete: %s (%.1fs)", silver, time.monotonic() - stage_started_at)

        stage_started_at = time.monotonic()
        logger.info("Starting gold aggregation")
        gold = run_aggregation_pipeline(db, target_symbols)
        logger.info("Gold aggregation complete: %s (%.1fs)", gold, time.monotonic() - stage_started_at)

        result = {
            "symbols": target_symbols,
            "bronze": bronze,
            "silver": silver,
            "gold": gold,
        }
        logger.info("Tracked-assets update complete in %.1fs", time.monotonic() - started_at)
        return result
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the project medallion ETL pipeline")
    parser.add_argument("symbols", nargs="*", help="Optional symbol list. If omitted, uses default project list.")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    result = run_etl(args.symbols)
    print(result)


if __name__ == "__main__":
    main()

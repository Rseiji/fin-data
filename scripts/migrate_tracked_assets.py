"""Migrate tracked_assets columns for databases created before the catalog schema.

Usage:
    PYTHONPATH=. python scripts/migrate_tracked_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrastructure.database.engine import DATABASE_SCHEMA, engine


def migrate_tracked_assets() -> None:
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DATABASE_SCHEMA}"'))
        for table_name in ("tracked_assets", "bronze_quotes", "silver_quotes", "gold_daily_summaries"):
            connection.execute(
                text(
                    f'ALTER TABLE IF EXISTS public."{table_name}" '
                    f'SET SCHEMA "{DATABASE_SCHEMA}"'
                )
            )

    columns = {
        column["name"]
        for column in inspect(engine).get_columns("tracked_assets", schema=DATABASE_SCHEMA)
    }

    with engine.begin() as connection:
        if "provider_symbol" not in columns:
            connection.execute(
                text(
                    f'ALTER TABLE "{DATABASE_SCHEMA}".tracked_assets '
                    "ADD COLUMN provider_symbol VARCHAR(128) NOT NULL DEFAULT ''"
                )
            )
        if "provider_config" not in columns:
            connection.execute(
                text(
                    f'ALTER TABLE "{DATABASE_SCHEMA}".tracked_assets '
                    "ADD COLUMN provider_config JSON NOT NULL DEFAULT '{}'"
                )
            )


if __name__ == "__main__":
    migrate_tracked_assets()
    print(f"Migrated tracked_assets in schema {DATABASE_SCHEMA}")
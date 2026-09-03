"""Point the existing NEAR tracked asset at Binance.

Usage:
    PYTHONPATH=. python scripts/migrate_near_to_binance.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import settings
from src.infrastructure.database.engine import engine


def migrate_near_to_binance() -> int:
    with engine.begin() as connection:
        result = connection.execute(
            text(
                f'UPDATE "{settings.database_schema}".tracked_assets '
                "SET source = 'binance', provider_symbol = 'NEARUSDT', "
                "provider_config = '{\"interval\": \"1d\"}'::json "
                "WHERE symbol = 'NEAR' AND asset_type = 'crypto'"
            )
        )
    return result.rowcount


if __name__ == "__main__":
    updated = migrate_near_to_binance()
    print(f"Updated {updated} NEAR tracked asset(s) to Binance")
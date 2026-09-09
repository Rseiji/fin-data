"""Point supported crypto assets at Binance's USDT spot pairs.

Usage:
    PYTHONPATH=. python scripts/migrate_crypto_to_binance.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import settings
from src.infrastructure.database.engine import engine


BINANCE_PAIRS = {
    "PENDLE": "PENDLEUSDT",
    "LINK": "LINKUSDT",
    "ENA": "ENAUSDT",
    "SYRUP": "SYRUPUSDT",
    "SUI": "SUIUSDT",
    "AAVE": "AAVEUSDT",
    "SOLUSD": "SOLUSDT",
    "BTCUSD": "BTCUSDT",
    "ETHUSD": "ETHUSDT",
}


def migrate_crypto_to_binance() -> int:
    updated = 0
    with engine.begin() as connection:
        for symbol, provider_symbol in BINANCE_PAIRS.items():
            result = connection.execute(
                text(
                    f'UPDATE "{settings.database_schema}".tracked_assets '
                    "SET source = 'binance', provider_symbol = :provider_symbol, "
                    "provider_config = '{\"interval\": \"1d\"}'::json "
                    "WHERE symbol = :symbol AND asset_type = 'crypto'"
                ),
                {"symbol": symbol, "provider_symbol": provider_symbol},
            )
            updated += result.rowcount
    return updated


if __name__ == "__main__":
    updated = migrate_crypto_to_binance()
    print(f"Updated {updated} crypto tracked asset(s) to Binance")
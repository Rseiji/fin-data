"""Fetch the latest price for a symbol from the silver layer.

Usage:
    python scripts/latest_price.py PETR4
    python scripts/latest_price.py BTCUSD
"""

from __future__ import annotations

import os
import sys

from src.infrastructure.database.engine import SessionLocal
from src.infrastructure.database import repositories


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/latest_price.py <SYMBOL>")
        raise SystemExit(1)

    symbol = sys.argv[1].upper()
    db = SessionLocal()
    try:
        quote = repositories.find_latest_quote(db, symbol)
        if quote is None:
            print(f"No quote found for {symbol}")
            return

        print({
            "symbol": quote.symbol,
            "asset_type": quote.asset_type,
            "price": str(quote.price),
            "currency": quote.currency,
            "quote_date": quote.quote_date.isoformat(),
            "source": quote.source,
        })
    finally:
        db.close()


if __name__ == "__main__":
    main()

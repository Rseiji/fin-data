"""Simple database access helper.

Usage:
    python scripts/db_check.py
    python scripts/db_check.py --table bronze_quotes
    python scripts/db_check.py --table silver_quotes --limit 5
    python scripts/db_check.py --table gold_daily_summaries --limit 10
"""

from __future__ import annotations

import argparse
from typing import Optional

from sqlalchemy import text

from src.infrastructure.database.engine import engine


TABLES = {
    "bronze_quotes": "SELECT * FROM bronze_quotes ORDER BY ingested_at DESC LIMIT :limit",
    "silver_quotes": "SELECT * FROM silver_quotes ORDER BY quote_date DESC LIMIT :limit",
    "gold_daily_summaries": "SELECT * FROM gold_daily_summaries ORDER BY trade_date DESC LIMIT :limit",
}


def query_table(table_name: str, limit: int = 10):
    query = TABLES.get(table_name)
    if query is None:
        raise ValueError(f"Unsupported table: {table_name}. Available: {', '.join(TABLES.keys())}")

    with engine.connect() as conn:
        rows = conn.execute(text(query), {"limit": limit}).fetchall()
        return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect database tables directly")
    parser.add_argument("--table", choices=sorted(TABLES.keys()), default="silver_quotes", help="Table to query")
    parser.add_argument("--limit", type=int, default=10, help="Number of rows to fetch")
    args = parser.parse_args()

    rows = query_table(args.table, limit=args.limit)

    if not rows:
        print(f"No rows found in {args.table}")
        return

    print(f"Table: {args.table}")
    for row in rows:
        print(dict(row._mapping))


if __name__ == "__main__":
    main()

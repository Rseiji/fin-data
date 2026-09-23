"""Fetch a complete quote history or daily summary through the paginated API.

Usage:
    uv run python scripts/fetch_history.py BTCUSD
    uv run python scripts/fetch_history.py PETR4 --summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import requests

from src.api.client import (
    fetch_all_daily_summaries,
    fetch_all_quote_history,
)


DEFAULT_API_URL = "http://localhost:8000/api/v1"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a complete history from the fin-data API"
    )
    parser.add_argument("symbol", help="Ticker symbol, such as BTCUSD or PETR4")
    parser.add_argument("--summary", action="store_true", help="Fetch daily summaries")
    parser.add_argument(
        "--api-url",
        default=os.getenv("FIN_DATA_API_URL", DEFAULT_API_URL),
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument("--start", help="Optional inclusive start datetime")
    parser.add_argument("--end", help="Optional inclusive end datetime")
    parser.add_argument("--page-size", type=int, default=100, help="Items per request")
    args = parser.parse_args()

    try:
        fetch = fetch_all_daily_summaries if args.summary else fetch_all_quote_history
        result = fetch(
            args.symbol,
            args.api_url,
            start=args.start,
            end=args.end,
            page_size=args.page_size,
        )
    except (requests.RequestException, ValueError) as exc:
        print(f"Could not fetch history: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
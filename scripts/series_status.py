"""Fetch historical-series status metadata from the API.

Usage:
    uv run python scripts/series_status.py BTCUSD
    uv run python scripts/series_status.py BTCUSD ETHUSD
    FIN_DATA_API_URL=http://localhost:8000/api/v1 \
        uv run python scripts/series_status.py PETR4 VALE3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

import requests

DEFAULT_API_URL = "http://localhost:8000/api/v1"
DEFAULT_TIMEOUT = 30


def fetch_series_status(symbols: List[str], api_url: str) -> list[dict]:
    """Request status metadata for symbols in the order supplied."""
    response = requests.get(
        f"{api_url.rstrip('/')}/quotes/status",
        params=[("symbols", symbol.upper()) for symbol in symbols],
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch historical-series status metadata from fin-data API"
    )
    parser.add_argument("symbols", nargs="+", help="One or more ticker symbols")
    parser.add_argument(
        "--api-url",
        default=os.getenv("FIN_DATA_API_URL", DEFAULT_API_URL),
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    args = parser.parse_args()

    try:
        result = fetch_series_status(args.symbols, args.api_url)
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        print(f"API request failed: {detail}", file=sys.stderr)
        raise SystemExit(1) from exc
    except requests.RequestException as exc:
        print(f"Could not reach API: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()

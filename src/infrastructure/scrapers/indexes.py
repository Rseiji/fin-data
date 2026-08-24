"""Brazilian macro-economic index scrapers (IPCA, CDI, SELIC)."""
import json
import logging
from datetime import date
from typing import Any, Dict, Iterable, List

from src.infrastructure.scrapers.base import fetch_json

logger = logging.getLogger(__name__)

# Banco Central do Brasil open data API (BCB/SGS)
BCB_SERIES_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{n}?formato=json"

# BCB time-series codes
BCB_CODES: Dict[str, int] = {
    "SELIC": 432,    # Taxa Selic – diária
    "CDI": 12,       # CDI diário
    "IPCA": 433,     # IPCA mensal
}


class IndexScraper:
    asset_type = "index"
    symbols = list(BCB_CODES.keys())

    def fetch_latest(self, symbol: str) -> List[Dict[str, Any]]:
        return scrape_bcb_series(symbol, last_n=1)

    def fetch_history(self, symbol: str, lookback_days: int = 0) -> List[Dict[str, Any]]:
        return scrape_bcb_series(symbol, last_n=max(lookback_days, 1))

    def fetch_all(
        self,
        symbols: Iterable[str] | None = None,
        lookback_days: int = 0,
    ) -> List[Dict[str, Any]]:
        return scrape_all_indexes(lookback_days, list(symbols) if symbols is not None else self.symbols)


def scrape_bcb_series(series_name: str, last_n: int = 1) -> List[Dict[str, Any]]:
    """Fetch the last N values of a BCB time series."""
    code = BCB_CODES.get(series_name.upper())
    if code is None:
        raise ValueError(f"Unknown BCB series: {series_name}")

    url = BCB_SERIES_URL.format(code=code, n=last_n)
    data = fetch_json(url)

    results = []
    for entry in data:
        results.append(
            {
                "symbol": series_name.upper(),
                "asset_type": "index",
                "source": "bcb",
                "value": entry.get("valor"),
                "date": entry.get("data"),
            }
        )
    return results


def scrape_all_indexes(lookback_days: int = 0, symbols: Iterable[str] | None = None) -> List[Dict[str, Any]]:
    """Scrape latest values for all tracked Brazilian indexes."""
    results = []
    target_symbols = list(symbols) if symbols is not None else list(BCB_CODES)
    for name in target_symbols:
        try:
            data = scrape_bcb_series(name, last_n=max(lookback_days, 1))
            results.extend(data)
            logger.info("Fetched index %s: %s", name, data)
        except Exception as exc:
            logger.error("Failed to fetch index %s: %s", name, exc)
    return results

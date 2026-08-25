"""Brazilian macro-economic index scrapers (IPCA, CDI, SELIC)."""
import json
import logging
from datetime import date
from typing import Any, Dict, Iterable, List

from src.infrastructure.scrapers.base import fetch_json
from src.infrastructure.database.models import TrackedAsset

logger = logging.getLogger(__name__)

# Banco Central do Brasil open data API (BCB/SGS)
BCB_SERIES_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{n}?formato=json"

class IndexScraper:
    asset_type = "index"

    def fetch_latest(self, asset: TrackedAsset) -> List[Dict[str, Any]]:
        return scrape_bcb_series(asset.symbol, last_n=1, asset=asset)

    def fetch_history(self, asset: TrackedAsset, lookback_days: int = 0) -> List[Dict[str, Any]]:
        return scrape_bcb_series(asset.symbol, last_n=max(lookback_days, 1), asset=asset)

    def fetch_all(
        self,
        symbols: Iterable[str | TrackedAsset] | None = None,
        lookback_days: int = 0,
    ) -> List[Dict[str, Any]]:
        if symbols is None:
            raise ValueError("symbols must be provided from the asset catalog")
        return scrape_all_indexes(lookback_days, list(symbols))


def scrape_bcb_series(series_name: str, last_n: int = 1, asset: TrackedAsset | None = None) -> List[Dict[str, Any]]:
    """Fetch the last N values of a BCB time series."""
    code = asset.provider_symbol if asset is not None else None
    if code is None:
        raise ValueError(f"Provider symbol is required for BCB series: {series_name}")

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


def scrape_all_indexes(lookback_days: int = 0, symbols: Iterable[str | TrackedAsset] | None = None,
                       assets: Iterable[TrackedAsset] | None = None) -> List[Dict[str, Any]]:
    """Scrape latest values for all tracked Brazilian indexes."""
    results = []
    target_assets = list(assets) if assets is not None else [asset for asset in (symbols or []) if isinstance(asset, TrackedAsset)]
    for asset in target_assets:
        name = asset.symbol
        try:
            data = scrape_bcb_series(name, last_n=max(lookback_days, 1), asset=asset)
            results.extend(data)
            logger.info("Fetched index %s: %s", name, data)
        except Exception as exc:
            logger.error("Failed to fetch index %s: %s", name, exc)
    return results

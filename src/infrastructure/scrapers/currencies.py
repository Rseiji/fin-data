"""Currency exchange rate scraper using exchangerate.host (free tier)."""
import logging
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List

from src.infrastructure.scrapers.base import fetch_json
from src.infrastructure.database.models import TrackedAsset

logger = logging.getLogger(__name__)

# Open exchange rates API (free, no key required for basic usage)
OPEN_RATES_URL = "https://open.er-api.com/v6/latest/{base}"

class CurrencyScraper:
    asset_type = "currency"

    def fetch_latest(self, asset: TrackedAsset) -> Dict[str, Any]:
        return scrape_currency_pair(asset)

    def fetch_history(self, asset: TrackedAsset, lookback_days: int = 0) -> List[Dict[str, Any]]:
        return scrape_currencies([asset], lookback_days=lookback_days)

    def fetch_all(
        self,
        symbols: Iterable[str | TrackedAsset] | None = None,
        lookback_days: int = 0,
    ) -> List[Dict[str, Any]]:
        if symbols is None:
            raise ValueError("symbols must be provided from the asset catalog")
        return scrape_currencies(list(symbols), lookback_days)


def scrape_currency_pair(asset: TrackedAsset) -> Dict[str, Any]:
    """Fetch the exchange rate for a single currency pair."""
    symbol = asset.symbol
    base = asset.provider_config["base"]
    quote = asset.provider_config["quote"]
    url = OPEN_RATES_URL.format(base=base)
    data = fetch_json(url)

    rates = data.get("rates", {})
    rate = rates.get(quote)
    if rate is None:
        raise ValueError(f"Rate {quote} not found in response for base {base}")

    return {
        "symbol": symbol.upper(),
        "asset_type": "currency",
        "source": "open_er_api",
        "price": rate,
        "currency": quote,
        "base": base,
        "last_updated": data.get("time_last_update_utc"),
    }


def scrape_currencies(
    symbols: Iterable[str | TrackedAsset] | None = None,
    lookback_days: int = 0,
    assets: Iterable[TrackedAsset] | None = None,
    lookback_by_symbol: Dict[str, int] | None = None,
) -> List[Dict[str, Any]]:
    """Scrape a list of currency pairs.

    When multiple symbols share the same base currency, fetch the base once and
    expand the results per symbol. This avoids redundant requests for the same base.
    """
    if assets is not None:
        symbols = list(assets)
    if symbols is None:
        raise ValueError("assets or symbols must be provided; load tracked assets from the database")
    requested = list(symbols)
    asset_by_symbol = {asset.symbol: asset for asset in requested if isinstance(asset, TrackedAsset)}
    symbol_names = [asset.symbol if isinstance(asset, TrackedAsset) else asset for asset in requested]
    if lookback_days > 0:
        results = []
        today = date.today()
        grouped_by_base: Dict[str, List[str]] = {}
        for sym in symbol_names:
            asset = asset_by_symbol.get(sym)
            if asset is None:
                continue
            grouped_by_base.setdefault(asset.provider_config["base"], []).append(sym)

        for base, base_symbols in grouped_by_base.items():
            quote_symbols = [asset_by_symbol[sym].provider_config["quote"] for sym in base_symbols]
            try:
                data = fetch_json(
                    f"https://api.frankfurter.app/{(today - timedelta(days=max(1, max((lookback_by_symbol or {}).get(sym, lookback_days) for sym in base_symbols)))).isoformat()}..{today.isoformat()}",
                    params={"from": base, "to": ",".join(quote_symbols)},
                )
                for sym in base_symbols:
                    quote = asset_by_symbol[sym].provider_config["quote"]
                    for day_str, day_rates in data.get("rates", {}).items():
                        rate = day_rates.get(quote)
                        if rate is not None:
                            results.append(
                                {
                                    "symbol": sym.upper(),
                                    "asset_type": "currency",
                                    "source": "frankfurter",
                                    "price": rate,
                                    "currency": quote,
                                    "base": base,
                                    "date": day_str,
                                }
                            )
            except Exception as exc:
                logger.error("Failed to fetch currency history for base %s: %s", base, exc)
        return results

    results = []
    grouped_by_base: Dict[str, List[str]] = {}
    for sym in symbol_names:
        asset = asset_by_symbol.get(sym)
        if asset is None:
            continue
        grouped_by_base.setdefault(asset.provider_config["base"], []).append(sym)

    for base, base_symbols in grouped_by_base.items():
        try:
            data = fetch_json(OPEN_RATES_URL.format(base=base))
            rates = data.get("rates", {})
            for sym in base_symbols:
                asset = asset_by_symbol.get(sym)
                if asset is None:
                    continue
                quote = asset.provider_config["quote"]
                rate = rates.get(quote)
                if rate is None:
                    raise ValueError(f"Rate {quote} not found in response for base {base}")
                results.append({
                    "symbol": sym.upper(),
                    "asset_type": "currency",
                    "source": asset.source,
                    "price": rate,
                    "currency": quote,
                    "base": base,
                    "last_updated": data.get("time_last_update_utc"),
                })
                logger.info("Fetched currency %s", sym)
        except Exception as exc:
            logger.error("Failed to fetch currency base %s: %s", base, exc)
    return results

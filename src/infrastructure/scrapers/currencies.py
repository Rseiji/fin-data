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
) -> List[Dict[str, Any]]:
    """Scrape a list of currency pairs."""
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
        start_date = today - timedelta(days=lookback_days)
        for sym in symbol_names:
            asset = asset_by_symbol.get(sym)
            if asset is None:
                continue
            base = asset.provider_config["base"]
            quote = asset.provider_config["quote"]
            try:
                data = fetch_json(
                    f"https://api.frankfurter.app/{start_date.isoformat()}..{today.isoformat()}",
                    params={"from": base, "to": quote},
                )
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
                logger.error("Failed to fetch currency %s history: %s", sym, exc)
        return results

    results = []
    for sym in symbol_names:
        try:
            asset = asset_by_symbol.get(sym)
            if asset is None:
                continue
            base = asset.provider_config["base"]
            quote = asset.provider_config["quote"]
            data = fetch_json(OPEN_RATES_URL.format(base=base))
            rate = data.get("rates", {}).get(quote)
            if rate is None:
                raise ValueError(f"Rate {quote} not found in response for base {base}")
            results.append({"symbol": sym.upper(), "asset_type": "currency", "source": asset.source,
                            "price": rate, "currency": quote, "base": base,
                            "last_updated": data.get("time_last_update_utc")})
            logger.info("Fetched currency %s", sym)
        except Exception as exc:
            logger.error("Failed to fetch currency %s: %s", sym, exc)
    return results

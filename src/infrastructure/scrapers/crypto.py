"""Crypto price scraper using CoinGecko public API (no key required)."""
import logging
from typing import Any, Dict, Iterable, List

from src.infrastructure.scrapers.base import fetch_json
from src.infrastructure.database.models import TrackedAsset

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

class CryptoScraper:
    asset_type = "crypto"

    def fetch_latest(self, symbol: str) -> Dict[str, Any]:
        return next(
            record for record in self.fetch_all(symbols=[symbol], lookback_days=0)
            if record["symbol"] == symbol
        )

    def fetch_history(self, symbol: str, lookback_days: int = 0) -> List[Dict[str, Any]]:
        return self.fetch_all(symbols=[symbol], lookback_days=lookback_days)

    def fetch_all(
        self,
        symbols: Iterable[str | TrackedAsset] | None = None,
        lookback_days: int = 0,
    ) -> List[Dict[str, Any]]:
        if symbols is None:
            raise ValueError("symbols must be provided from the asset catalog")
        return scrape_crypto_prices(list(symbols), lookback_days)


def scrape_crypto_prices(
    symbols: Iterable[str | TrackedAsset] | None = None,
    lookback_days: int = 0,
    assets: Iterable[TrackedAsset] | None = None,
) -> List[Dict[str, Any]]:
    """
    Fetch current prices from CoinGecko.

    Returns a list of raw price dicts, one per symbol.
    """
    if assets is not None:
        assets = list(assets)
        symbols = assets
    if symbols is None:
        raise ValueError("assets or symbols must be provided; load tracked assets from the database")
    requested = list(symbols)
    asset_by_symbol = {
        asset.symbol: asset for asset in requested if isinstance(asset, TrackedAsset)
    }
    symbol_names = [asset.symbol if isinstance(asset, TrackedAsset) else asset for asset in requested]

    coin_ids = [asset_by_symbol[s].provider_symbol for s in symbol_names if s in asset_by_symbol]
    if not coin_ids:
        logger.warning("No valid crypto symbols requested")
        return []

    if lookback_days > 0:
        results = []
        for sym in symbol_names:
            asset = asset_by_symbol.get(sym)
            if asset is None:
                continue
            coin_id = asset.provider_symbol
            data = fetch_json(
                f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
                params={"vs_currency": "usd", "days": lookback_days},
            )
            for timestamp, price in data.get("prices", []):
                results.append(
                    {
                        "symbol": sym,
                        "asset_type": "crypto",
                        "source": "coingecko",
                        "price": price,
                        "currency": "USD",
                        "timestamp": timestamp / 1000,
                    }
                )
        return results

    url = f"{COINGECKO_BASE}/simple/price"
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": "usd",
        "include_last_updated_at": "true",
        "include_24hr_change": "true",
    }
    data = fetch_json(url, params=params)

    results = []
    for sym in symbol_names:
        asset = asset_by_symbol.get(sym)
        if asset is None or asset.provider_symbol not in data:
            continue
        coin_data = data[asset.provider_symbol]
        results.append(
            {
                "symbol": sym,
                "asset_type": "crypto",
                "source": "coingecko",
                "price": coin_data.get("usd"),
                "pct_change_24h": coin_data.get("usd_24h_change"),
                "last_updated_at": coin_data.get("last_updated_at"),
            }
        )
        logger.info("Fetched %s price: %s", sym, coin_data.get("usd"))

    return results

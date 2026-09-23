"""Crypto price scrapers for CoinGecko and Binance public APIs."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List

import requests

from src.infrastructure.scrapers.base import fetch_json
from src.infrastructure.database.models import TrackedAsset

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
BINANCE_BASE = "https://api.binance.com/api/v3"
BINANCE_KLINE_LIMIT = 1000

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
    lookback_by_symbol: Dict[str, int] | None = None,
) -> List[Dict[str, Any]]:
    """Fetch current or historical prices using each asset's configured source."""
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

    assets_by_source = {
        "binance": [
            asset for asset in asset_by_symbol.values() if asset.source == "binance"
        ],
        "coingecko": [
            asset for asset in asset_by_symbol.values() if asset.source != "binance"
        ],
    }
    if not asset_by_symbol:
        logger.warning("No valid crypto symbols requested")
        return []

    results = []
    for asset in assets_by_source.get("binance", []):
        symbol_lookback = (lookback_by_symbol or {}).get(asset.symbol, lookback_days)
        try:
            results.extend(_scrape_binance_asset(asset, symbol_lookback))
        except requests.RequestException as exc:
            logger.error("Failed to fetch crypto %s from Binance: %s", asset.symbol, exc)

    coingecko_assets = assets_by_source.get("coingecko", [])
    coin_ids = [asset.provider_symbol for asset in coingecko_assets]
    if coingecko_assets and lookback_days > 0:
        for asset in coingecko_assets:
            symbol_lookback = (lookback_by_symbol or {}).get(asset.symbol, lookback_days)
            try:
                data = fetch_json(
                    f"{COINGECKO_BASE}/coins/{asset.provider_symbol}/market_chart",
                    params={"vs_currency": "usd", "days": max(1, symbol_lookback)},
                )
            except requests.RequestException as exc:
                logger.error("Failed to fetch crypto %s: %s", asset.symbol, exc)
                continue
            results.extend(
                {
                    "symbol": asset.symbol,
                    "asset_type": "crypto",
                    "source": "coingecko",
                    "price": price,
                    "currency": "USD",
                    "timestamp": timestamp / 1000,
                }
                for timestamp, price in data.get("prices", [])
            )
    elif coingecko_assets:
        data = fetch_json(
            f"{COINGECKO_BASE}/simple/price",
            params={
                "ids": ",".join(coin_ids),
                "vs_currencies": "usd",
                "include_last_updated_at": "true",
                "include_24hr_change": "true",
            },
        )
        for asset in coingecko_assets:
            if asset.provider_symbol not in data:
                continue
            coin_data = data[asset.provider_symbol]
            results.append(
                {
                    "symbol": asset.symbol,
                    "asset_type": "crypto",
                    "source": "coingecko",
                    "price": coin_data.get("usd"),
                    "pct_change_24h": coin_data.get("usd_24h_change"),
                    "last_updated_at": coin_data.get("last_updated_at"),
                }
            )
            logger.info("Fetched %s price: %s", asset.symbol, coin_data.get("usd"))

    return results


def _scrape_binance_asset(asset: TrackedAsset, lookback_days: int) -> List[Dict[str, Any]]:
    """Fetch daily Binance candles, paging because the API caps each response."""
    if lookback_days <= 0:
        data = fetch_json(
            f"{BINANCE_BASE}/ticker/price",
            params={"symbol": asset.provider_symbol.upper()},
        )
        return [{
            "symbol": asset.symbol,
            "asset_type": "crypto",
            "source": "binance",
            "price": float(data["price"]),
            "currency": "USDT",
        }]

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    results: List[Dict[str, Any]] = []
    while start < end:
        data = fetch_json(
            f"{BINANCE_BASE}/klines",
            params={
                "symbol": asset.provider_symbol.upper(),
                "interval": "1d",
                "startTime": int(start.timestamp() * 1000),
                "endTime": int(end.timestamp() * 1000),
                "limit": BINANCE_KLINE_LIMIT,
            },
        )
        if not data:
            break
        for candle in data:
            results.append(
                {
                    "symbol": asset.symbol,
                    "asset_type": "crypto",
                    "source": "binance",
                    "price": float(candle[4]),
                    "currency": "USDT",
                    "timestamp": candle[0] / 1000,
                }
            )
        next_start = datetime.fromtimestamp(data[-1][0] / 1000, tz=timezone.utc) + timedelta(days=1)
        if next_start <= start:
            break
        start = next_start
    return results

"""Crypto price scraper using CoinGecko public API (no key required)."""
import logging
from typing import Any, Dict, Iterable, List

from src.infrastructure.scrapers.base import fetch_json

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Map of trading symbol -> CoinGecko coin id
CRYPTO_SYMBOLS: Dict[str, str] = {
    "BTCUSD": "bitcoin",
    "ETHUSD": "ethereum",
    "BNBUSD": "binancecoin",
    "SOLUSD": "solana",
    "ADAUSD": "cardano",
}


class CryptoScraper:
    asset_type = "crypto"
    symbols = list(CRYPTO_SYMBOLS.keys())

    def fetch_latest(self, symbol: str) -> Dict[str, Any]:
        return next(
            record for record in self.fetch_all(symbols=[symbol], lookback_days=0)
            if record["symbol"] == symbol
        )

    def fetch_history(self, symbol: str, lookback_days: int = 0) -> List[Dict[str, Any]]:
        return self.fetch_all(symbols=[symbol], lookback_days=lookback_days)

    def fetch_all(
        self,
        symbols: Iterable[str] | None = None,
        lookback_days: int = 0,
    ) -> List[Dict[str, Any]]:
        return scrape_crypto_prices(list(symbols) if symbols is not None else self.symbols, lookback_days)


def scrape_crypto_prices(
    symbols: List[str] | None = None, lookback_days: int = 0
) -> List[Dict[str, Any]]:
    """
    Fetch current prices from CoinGecko.

    Returns a list of raw price dicts, one per symbol.
    """
    if symbols is None:
        symbols = list(CRYPTO_SYMBOLS.keys())

    coin_ids = [CRYPTO_SYMBOLS[s] for s in symbols if s in CRYPTO_SYMBOLS]
    if not coin_ids:
        logger.warning("No valid crypto symbols requested")
        return []

    if lookback_days > 0:
        results = []
        for sym, coin_id in CRYPTO_SYMBOLS.items():
            if sym not in symbols:
                continue
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
    for sym, coin_id in CRYPTO_SYMBOLS.items():
        if sym not in symbols or coin_id not in data:
            continue
        coin_data = data[coin_id]
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

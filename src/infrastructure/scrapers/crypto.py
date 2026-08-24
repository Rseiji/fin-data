"""Crypto price scraper using CoinGecko public API (no key required)."""
import logging
from typing import Dict, Any, List

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


def scrape_crypto_prices(symbols: List[str] | None = None) -> List[Dict[str, Any]]:
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

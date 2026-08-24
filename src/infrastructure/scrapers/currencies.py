"""Currency exchange rate scraper using exchangerate.host (free tier)."""
import logging
from typing import Any, Dict, List

from src.infrastructure.scrapers.base import fetch_json

logger = logging.getLogger(__name__)

# Open exchange rates API (free, no key required for basic usage)
OPEN_RATES_URL = "https://open.er-api.com/v6/latest/{base}"

# Map of symbol -> (base currency, quote currency)
CURRENCY_PAIRS: Dict[str, tuple[str, str]] = {
    "USDBRL": ("USD", "BRL"),
    "JPYBRL": ("JPY", "BRL"),
    "USDEUR": ("USD", "EUR"),
    "EURUSD": ("EUR", "USD"),
    "GBPBRL": ("GBP", "BRL"),
}


def scrape_currency_pair(symbol: str) -> Dict[str, Any]:
    """Fetch the exchange rate for a single currency pair."""
    pair = CURRENCY_PAIRS.get(symbol.upper())
    if pair is None:
        raise ValueError(f"Unknown currency pair: {symbol}")

    base, quote = pair
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


def scrape_currencies(symbols: List[str] | None = None) -> List[Dict[str, Any]]:
    """Scrape a list of currency pairs."""
    if symbols is None:
        symbols = list(CURRENCY_PAIRS.keys())
    results = []
    for sym in symbols:
        try:
            results.append(scrape_currency_pair(sym))
            logger.info("Fetched currency %s", sym)
        except Exception as exc:
            logger.error("Failed to fetch currency %s: %s", sym, exc)
    return results

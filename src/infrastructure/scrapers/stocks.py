"""Brazilian stock / ETF price scraper using Yahoo Finance API (unofficial)."""
import logging
from typing import Any, Dict, List

from src.infrastructure.scrapers.base import fetch_json

logger = logging.getLogger(__name__)

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

# Brazilian stocks traded on B3 (suffix .SA for Yahoo)
STOCK_SYMBOLS: List[str] = [
    "PETR4",
    "ITUB4",
    "SAPR11",
    "CEAB3",
    "VALE3",
    "BBAS3",
    "WEGE3",
    "RENT3",
]

# Brazilian ETFs
ETF_SYMBOLS: List[str] = [
    "IVVB11",
    "BOVA11",
    "DIVO11",
    "SMAL11",
    "XFIX11",
]


def _yahoo_ticker(symbol: str) -> str:
    return f"{symbol}.SA"


def scrape_b3_quote(symbol: str) -> Dict[str, Any]:
    """Fetch the latest quote for a single B3 ticker via Yahoo Finance."""
    ticker = _yahoo_ticker(symbol)
    url = YAHOO_QUOTE_URL.format(ticker=ticker)
    params = {"interval": "1d", "range": "1d"}
    data = fetch_json(url, params=params)

    result_data = data.get("chart", {}).get("result", [])
    if not result_data:
        raise ValueError(f"No data returned for {symbol}")

    meta = result_data[0].get("meta", {})
    return {
        "symbol": symbol,
        "asset_type": "stock",
        "source": "yahoo_finance",
        "price": meta.get("regularMarketPrice"),
        "currency": meta.get("currency", "BRL"),
        "previous_close": meta.get("chartPreviousClose"),
        "exchange_timezone": meta.get("exchangeTimezoneName"),
        "timestamp": meta.get("regularMarketTime"),
    }


def scrape_etf_quote(symbol: str) -> Dict[str, Any]:
    """Fetch the latest quote for a single ETF ticker via Yahoo Finance."""
    result = scrape_b3_quote(symbol)
    result["asset_type"] = "etf"
    return result


def scrape_stocks(symbols: List[str] | None = None) -> List[Dict[str, Any]]:
    """Scrape a list of stock symbols (defaults to STOCK_SYMBOLS)."""
    if symbols is None:
        symbols = STOCK_SYMBOLS
    results = []
    for sym in symbols:
        try:
            results.append(scrape_b3_quote(sym))
            logger.info("Fetched stock %s", sym)
        except Exception as exc:
            logger.error("Failed to fetch stock %s: %s", sym, exc)
    return results


def scrape_etfs(symbols: List[str] | None = None) -> List[Dict[str, Any]]:
    """Scrape a list of ETF symbols (defaults to ETF_SYMBOLS)."""
    if symbols is None:
        symbols = ETF_SYMBOLS
    results = []
    for sym in symbols:
        try:
            results.append(scrape_etf_quote(sym))
            logger.info("Fetched ETF %s", sym)
        except Exception as exc:
            logger.error("Failed to fetch ETF %s: %s", sym, exc)
    return results

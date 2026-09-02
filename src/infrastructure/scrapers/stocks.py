"""Brazilian stock / ETF price scraper using Yahoo Finance API (unofficial)."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List

from src.infrastructure.scrapers.base import fetch_json
from src.infrastructure.database.models import TrackedAsset

logger = logging.getLogger(__name__)

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

class StockScraper:
    asset_type = "stock"

    def fetch_latest(self, symbol: str) -> Dict[str, Any]:
        return scrape_b3_quote(symbol)

    def fetch_history(self, symbol: str, lookback_days: int = 0) -> List[Dict[str, Any]]:
        return scrape_b3_history(symbol, lookback_days=lookback_days)

    def fetch_all(
        self,
        symbols: Iterable[str | TrackedAsset] | None = None,
        lookback_days: int = 0,
    ) -> List[Dict[str, Any]]:
        if symbols is None:
            raise ValueError("symbols must be provided from the asset catalog")
        return scrape_stocks(list(symbols), lookback_days)


class ETFScraper:
    asset_type = "etf"

    def fetch_latest(self, symbol: str) -> Dict[str, Any]:
        return scrape_etf_quote(symbol)

    def fetch_history(self, symbol: str, lookback_days: int = 0) -> List[Dict[str, Any]]:
        history = scrape_b3_history(symbol, lookback_days=lookback_days)
        for record in history:
            record["asset_type"] = "etf"
        return history

    def fetch_all(
        self,
        symbols: Iterable[str | TrackedAsset] | None = None,
        lookback_days: int = 0,
    ) -> List[Dict[str, Any]]:
        if symbols is None:
            raise ValueError("symbols must be provided from the asset catalog")
        return scrape_etfs(list(symbols), lookback_days)


def _asset_symbol(asset: str | TrackedAsset) -> str:
    return asset if isinstance(asset, str) else asset.symbol


def _yahoo_ticker(asset: str | TrackedAsset) -> str:
    if isinstance(asset, TrackedAsset) and asset.provider_symbol:
        return asset.provider_symbol
    return f"{asset}.SA"


def scrape_b3_quote(symbol: str | TrackedAsset) -> Dict[str, Any]:
    """Fetch the latest quote for a single B3 ticker via Yahoo Finance."""
    canonical_symbol = _asset_symbol(symbol)
    ticker = _yahoo_ticker(symbol)
    url = YAHOO_QUOTE_URL.format(ticker=ticker)
    params = {"interval": "1d", "range": "1d"}
    data = fetch_json(url, params=params)

    result_data = data.get("chart", {}).get("result", [])
    if not result_data:
        raise ValueError(f"No data returned for {canonical_symbol}")

    meta = result_data[0].get("meta", {})
    return {
        "symbol": canonical_symbol,
        "asset_type": "stock",
        "source": "yahoo_finance",
        "price": meta.get("regularMarketPrice"),
        "currency": meta.get("currency", "BRL"),
        "previous_close": meta.get("chartPreviousClose"),
        "exchange_timezone": meta.get("exchangeTimezoneName"),
        "timestamp": meta.get("regularMarketTime"),
    }


def scrape_b3_history(symbol: str | TrackedAsset, lookback_days: int = 6) -> List[Dict[str, Any]]:
    """Fetch daily closing prices for the requested lookback window.

    Yahoo Finance chart endpoint accepts explicit Unix timestamps for custom
    windows; using a raw "2190d" range token is not supported for long lookbacks
    and can collapse the response to the latest day only.
    """
    if lookback_days <= 0:
        lookback_days = 1

    end_ts = datetime.now(tz=timezone.utc)
    start_ts = end_ts - timedelta(days=lookback_days)

    data = fetch_json(
        YAHOO_QUOTE_URL.format(ticker=_yahoo_ticker(symbol)),
        params={
            "interval": "1d",
            "period1": int(start_ts.timestamp()),
            "period2": int(end_ts.timestamp()),
        },
    )
    result_data = data.get("chart", {}).get("result", [])
    if not result_data:
        raise ValueError(f"No data returned for {_asset_symbol(symbol)}")

    chart = result_data[0]
    timestamps = chart.get("timestamp", [])
    closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    currency = chart.get("meta", {}).get("currency", "BRL")
    return [
        {
            "symbol": _asset_symbol(symbol),
            "asset_type": "stock",
            "source": "yahoo_finance",
            "price": close,
            "currency": currency,
            "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        }
        for ts, close in zip(timestamps, closes)
        if close is not None
    ]


def scrape_etf_quote(symbol: str | TrackedAsset) -> Dict[str, Any]:
    """Fetch the latest quote for a single ETF ticker via Yahoo Finance."""
    result = scrape_b3_quote(symbol)
    result["asset_type"] = "etf"
    return result


def scrape_stocks(
    symbols: Iterable[str | TrackedAsset] | None = None, lookback_days: int = 0
) -> List[Dict[str, Any]]:
    """Scrape the supplied list of stock symbols."""
    if symbols is None:
        raise ValueError("symbols must be provided; load tracked assets from the database")
    results = []
    for sym in symbols:
        try:
            if lookback_days > 0:
                results.extend(scrape_b3_history(sym, lookback_days))
            else:
                results.append(scrape_b3_quote(sym))
            logger.info("Fetched stock %s", sym)
        except Exception as exc:
            logger.error("Failed to fetch stock %s: %s", sym, exc)
    return results


def scrape_etfs(
    symbols: Iterable[str | TrackedAsset] | None = None, lookback_days: int = 0
) -> List[Dict[str, Any]]:
    """Scrape the supplied list of ETF symbols."""
    if symbols is None:
        raise ValueError("symbols must be provided; load tracked assets from the database")
    results = []
    for sym in symbols:
        try:
            if lookback_days > 0:
                history = scrape_b3_history(sym, lookback_days)
                for record in history:
                    record["asset_type"] = "etf"
                results.extend(history)
            else:
                results.append(scrape_etf_quote(sym))
            logger.info("Fetched ETF %s", sym)
        except Exception as exc:
            logger.error("Failed to fetch ETF %s: %s", sym, exc)
    return results

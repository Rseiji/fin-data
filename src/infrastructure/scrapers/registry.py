"""Registry/factory for scraper strategies."""
from __future__ import annotations

from typing import Dict, Iterable, Protocol

from src.infrastructure.scrapers.crypto import CryptoScraper
from src.infrastructure.scrapers.currencies import CurrencyScraper
from src.infrastructure.scrapers.indexes import IndexScraper
from src.infrastructure.scrapers.stocks import StockScraper, ETFScraper


class ScraperStrategy(Protocol):
    """Common interface for all source-specific scrapers."""

    asset_type: str
    symbols: list[str]

    def fetch_latest(self, symbol: str):
        ...

    def fetch_history(self, symbol: str, lookback_days: int = 0):
        ...

    def fetch_all(self, lookback_days: int = 0):
        ...


_SCRAPER_REGISTRY: Dict[str, ScraperStrategy] = {
    "stocks": StockScraper(),
    "etfs": ETFScraper(),
    "crypto": CryptoScraper(),
    "currency": CurrencyScraper(),
    "index": IndexScraper(),
}


def list_scrapers() -> list[str]:
    return list(_SCRAPER_REGISTRY.keys())


def get_scraper(name: str) -> ScraperStrategy:
    key = name.lower().strip()
    if key not in _SCRAPER_REGISTRY:
        raise ValueError(f"Unknown scraper: {name}")
    return _SCRAPER_REGISTRY[key]


def run_scraper(name: str, lookback_days: int = 0, symbols: Iterable[str] | None = None):
    scraper = get_scraper(name)
    if symbols is not None:
        return scraper.fetch_all(symbols=symbols, lookback_days=lookback_days)
    return scraper.fetch_all(lookback_days=lookback_days)

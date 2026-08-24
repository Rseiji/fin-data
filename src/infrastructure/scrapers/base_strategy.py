"""Base strategy contract shared by scraper implementations."""
from __future__ import annotations

from typing import Any, Iterable, List, Protocol


class BaseScraperStrategy(Protocol):
    """Minimal common interface for data scrapers."""

    asset_type: str
    symbols: list[str]

    def fetch_latest(self, symbol: str) -> dict[str, Any]:
        ...

    def fetch_history(self, symbol: str, lookback_days: int = 0) -> list[dict[str, Any]]:
        ...

    def fetch_all(
        self,
        symbols: Iterable[str] | None = None,
        lookback_days: int = 0,
    ) -> list[dict[str, Any]]:
        ...

"""Repository interfaces (protocols) for quotes."""
from typing import Protocol, List, Optional
from datetime import datetime

from src.domain.entities.quote import RawQuote, Quote, DailySummary


class RawQuoteRepository(Protocol):
    def save(self, raw_quote: RawQuote) -> None: ...
    def find_by_symbol(self, symbol: str, limit: int = 100) -> List[RawQuote]: ...


class QuoteRepository(Protocol):
    def save(self, quote: Quote) -> None: ...
    def find_by_symbol(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Quote]: ...
    def find_latest(self, symbol: str) -> Optional[Quote]: ...


class DailySummaryRepository(Protocol):
    def save(self, summary: DailySummary) -> None: ...
    def find_by_symbol(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[DailySummary]: ...

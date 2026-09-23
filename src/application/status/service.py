"""Application service for historical-series status metadata."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from statistics import mean, stdev, variance
from typing import List

from sqlalchemy.orm import Session

from src.infrastructure.database import repositories


@dataclass(frozen=True)
class SeriesStatus:
    symbol: str
    start_date: datetime
    last_date: datetime
    last_price: Decimal
    first_price: Decimal
    variance: Decimal
    standard_deviation: Decimal
    mean: Decimal
    granularity: str
    record_count: int


def _granularity(dates: List[datetime]) -> str:
    if len(dates) < 2:
        return "insufficient_data"

    intervals = sorted(
        (later - earlier).total_seconds()
        for earlier, later in zip(dates, dates[1:])
        if later >= earlier
    )
    if not intervals:
        return "insufficient_data"

    seconds = intervals[len(intervals) // 2]
    if seconds < 60:
        return "sub-minute"
    if seconds < 3600:
        return "minute"
    if seconds < 86400:
        return "hourly"
    if seconds < 172800:
        return "daily"
    if seconds < 604800:
        return "multi-day"
    return "weekly-or-longer"


def get_series_status(db: Session, symbol: str) -> SeriesStatus | None:
    quotes = repositories.find_quotes_by_symbol(db, symbol.upper())
    if not quotes:
        return None

    quotes = sorted(quotes, key=lambda quote: quote.quote_date)
    prices = [quote.price for quote in quotes]
    return SeriesStatus(
        symbol=quotes[0].symbol,
        start_date=quotes[0].quote_date,
        last_date=quotes[-1].quote_date,
        first_price=prices[0],
        last_price=prices[-1],
        variance=variance(prices) if len(prices) > 1 else Decimal("0"),
        standard_deviation=stdev(prices) if len(prices) > 1 else Decimal("0"),
        mean=mean(prices),
        granularity=_granularity([quote.quote_date for quote in quotes]),
        record_count=len(quotes),
    )


def get_series_statuses(db: Session, symbols: List[str]) -> List[SeriesStatus]:
    statuses = []
    for symbol in symbols:
        status = get_series_status(db, symbol)
        if status is not None:
            statuses.append(status)
    return statuses
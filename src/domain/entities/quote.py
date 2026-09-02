from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


@dataclass
class RawQuote:
    """Raw data as received from an external source (bronze)."""
    id: str
    symbol: str
    asset_type: str
    source: str
    raw_payload: str
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Quote:
    """Cleaned and validated quote (silver)."""
    id: str
    bronze_id: str
    symbol: str
    asset_type: str
    price: Decimal
    currency: str
    quote_date: datetime
    source: str
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DailySummary:
    """Aggregated daily summary (gold)."""
    id: str
    symbol: str
    asset_type: str
    trade_date: datetime
    open_price: Optional[Decimal]
    close_price: Optional[Decimal]
    high_price: Optional[Decimal]
    low_price: Optional[Decimal]
    pct_change: Optional[Decimal]
    currency: str
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

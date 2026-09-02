"""Unit tests for the gold aggregation layer."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.application.aggregation.aggregate import _compute_daily_summary, _group_by_date
from src.domain.entities.quote import Quote


def _make_quote(price: float, dt: datetime, symbol: str = "BTCUSD") -> Quote:
    return Quote(
        id="q1",
        bronze_id="b1",
        symbol=symbol,
        asset_type="crypto",
        price=Decimal(str(price)),
        currency="USD",
        quote_date=dt,
        source="test",
    )


def test_group_by_date():
    dt1 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)
    dt3 = datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc)
    quotes = [_make_quote(100, dt1), _make_quote(110, dt2), _make_quote(120, dt3)]
    grouped = _group_by_date(quotes)
    assert len(grouped) == 2
    assert len(grouped["2024-01-01"]) == 2
    assert len(grouped["2024-01-02"]) == 1


def test_compute_daily_summary():
    dt1 = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt3 = datetime(2024, 1, 1, 16, 0, tzinfo=timezone.utc)
    quotes = [_make_quote(100, dt1), _make_quote(115, dt2), _make_quote(105, dt3)]

    summary = _compute_daily_summary("BTCUSD", "crypto", "2024-01-01", quotes)
    assert summary.open_price == Decimal("100")
    assert summary.close_price == Decimal("105")
    assert summary.high_price == Decimal("115")
    assert summary.low_price == Decimal("100")
    assert summary.pct_change is not None
    assert abs(float(summary.pct_change) - 5.0) < 0.001

"""Unit tests for the silver transformation layer."""
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.application.transformation.transform import (
    _parse_price,
    _parse_timestamp,
    _raw_to_quote,
    transform_symbol,
)
from src.domain.entities.quote import Quote, RawQuote


def _make_raw(payload: dict, symbol: str = "BTCUSD", asset_type: str = "crypto") -> RawQuote:
    return RawQuote(
        id="test-id-1",
        symbol=symbol,
        asset_type=asset_type,
        source="coingecko",
        raw_payload=json.dumps(payload),
    )


def test_parse_price_valid():
    assert _parse_price("45000.5") == Decimal("45000.5")
    assert _parse_price(45000) == Decimal("45000")


def test_parse_price_none():
    assert _parse_price(None) is None


def test_parse_price_invalid():
    assert _parse_price("not-a-number") is None


def test_parse_timestamp_unix():
    ts = _parse_timestamp(1700000000)
    assert ts is not None
    assert ts.tzinfo is not None


def test_parse_timestamp_date_string():
    ts = _parse_timestamp("01/01/2024")
    assert ts is not None
    assert ts.year == 2024


def test_parse_timestamp_iso_with_timezone():
    ts = _parse_timestamp("2020-07-01T00:00:00+00:00")
    assert ts is not None
    assert ts.year == 2020
    assert ts.month == 7
    assert ts.day == 1


def test_raw_to_quote_success():
    payload = {
        "symbol": "BTCUSD",
        "asset_type": "crypto",
        "source": "coingecko",
        "price": 45000.0,
        "currency": "USD",
        "timestamp": 1700000000,
    }
    raw = _make_raw(payload)
    quote = _raw_to_quote(raw)
    assert quote is not None
    assert quote.symbol == "BTCUSD"
    assert quote.price == Decimal("45000.0")
    assert quote.currency == "USD"
    assert quote.bronze_id == "test-id-1"


def test_raw_to_quote_missing_price():
    payload = {"symbol": "BTCUSD", "asset_type": "crypto", "source": "coingecko"}
    raw = _make_raw(payload)
    quote = _raw_to_quote(raw)
    assert quote is None


def test_raw_to_quote_bad_json():
    raw = RawQuote(
        id="bad-id",
        symbol="X",
        asset_type="crypto",
        source="test",
        raw_payload="not-json",
    )
    quote = _raw_to_quote(raw)
    assert quote is None


def test_transform_symbol_skips_old_records(mocker):
    latest = Quote(
        id="latest-id",
        bronze_id="old-b",
        symbol="BTCUSD",
        asset_type="crypto",
        price=Decimal("100"),
        currency="USD",
        quote_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
        source="coingecko",
    )
    old_raw = _make_raw({"price": 90, "timestamp": 1704153600}, symbol="BTCUSD")
    new_raw = _make_raw({"price": 110, "timestamp": 1704240000}, symbol="BTCUSD")
    mocker.patch("src.application.transformation.transform.repositories.find_latest_quote", return_value=latest)
    mocker.patch("src.application.transformation.transform.repositories.find_raw_quotes_by_symbol", return_value=[old_raw, new_raw])
    save_quote = mocker.patch("src.application.transformation.transform.repositories.save_quote")

    count = transform_symbol(mocker.Mock(), "BTCUSD")

    assert count == 1
    assert save_quote.call_count == 1

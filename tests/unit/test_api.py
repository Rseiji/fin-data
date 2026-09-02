"""Unit tests for the FastAPI routes using TestClient."""
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.entities.quote import Quote, DailySummary
from src.infrastructure.database.engine import get_db


def _mock_db():
    return MagicMock()


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_db] = _mock_db
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_latest_quote_not_found(client, mocker):
    mocker.patch(
        "src.api.routers.quotes.repositories.find_latest_quote", return_value=None
    )
    resp = client.get("/api/v1/quotes/BTCUSD/latest")
    assert resp.status_code == 404


def test_latest_quote_found(client, mocker):
    quote = Quote(
        id="q1",
        bronze_id="b1",
        symbol="BTCUSD",
        asset_type="crypto",
        price=Decimal("45000"),
        currency="USD",
        quote_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source="coingecko",
        processed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    mocker.patch(
        "src.api.routers.quotes.repositories.find_latest_quote", return_value=quote
    )
    resp = client.get("/api/v1/quotes/BTCUSD/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "BTCUSD"
    assert data["price"] == "45000"


def test_quote_history(client, mocker):
    mocker.patch(
        "src.api.routers.quotes.repositories.find_quotes_by_symbol", return_value=[]
    )
    resp = client.get("/api/v1/quotes/BTCUSD/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_series_status_preserves_requested_order(client, mocker):
    def find_quotes(_db, symbol, start=None, end=None):
        quotes = {
            "ETHUSD": [
                Quote(
                    id="eth-1", bronze_id="b1", symbol="ETHUSD", asset_type="crypto",
                    price=Decimal("2000"), currency="USD",
                    quote_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    source="coingecko", processed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                ),
                Quote(
                    id="eth-2", bronze_id="b2", symbol="ETHUSD", asset_type="crypto",
                    price=Decimal("2200"), currency="USD",
                    quote_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
                    source="coingecko", processed_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
                ),
            ],
            "BTCUSD": [
                Quote(
                    id="btc-1", bronze_id="b3", symbol="BTCUSD", asset_type="crypto",
                    price=Decimal("40000"), currency="USD",
                    quote_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    source="coingecko", processed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                ),
            ],
        }
        return quotes.get(symbol, [])

    mocker.patch(
        "src.application.status.service.repositories.find_quotes_by_symbol",
        side_effect=find_quotes,
    )
    resp = client.get("/api/v1/quotes/status?symbols=BTCUSD&symbols=ETHUSD")

    assert resp.status_code == 200
    data = resp.json()
    assert [item["symbol"] for item in data] == ["BTCUSD", "ETHUSD"]
    assert data[0]["first_price"] == "40000"
    assert data[0]["last_price"] == "40000"
    assert data[0]["granularity"] == "insufficient_data"
    assert data[0]["record_count"] == 1
    assert data[1]["mean"] == "2100"
    assert data[1]["granularity"] == "daily"


def test_series_status_not_found(client, mocker):
    mocker.patch(
        "src.application.status.service.repositories.find_quotes_by_symbol",
        return_value=[],
    )
    resp = client.get("/api/v1/quotes/status?symbols=UNKNOWN")
    assert resp.status_code == 404

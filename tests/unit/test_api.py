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

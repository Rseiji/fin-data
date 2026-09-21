"""Unit tests for the FastAPI routes using TestClient."""
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import ANY, patch, MagicMock

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


def test_run_full_pipeline(client, mocker):
    mocker.patch(
        "src.api.routers.ingestion.run_ingestion_pipeline",
        return_value={"BTCUSD": 10},
    )
    mocker.patch(
        "src.api.routers.ingestion.repositories.list_enabled_symbols",
        return_value=["BTCUSD"],
    )
    mocker.patch(
        "src.api.routers.ingestion.run_transformation_pipeline",
        return_value={"BTCUSD": 8},
    )
    mocker.patch(
        "src.api.routers.ingestion.run_aggregation_pipeline",
        return_value={"BTCUSD": 2},
    )

    resp = client.post("/api/v1/ingestion/run")

    assert resp.status_code == 200
    assert resp.json() == {
        "ingested": {"BTCUSD": 10},
        "transformed": {"BTCUSD": 8},
        "aggregated": {"BTCUSD": 2},
    }


@pytest.mark.parametrize(
    ("failed_stage", "detail"),
    [
        ("run_ingestion_pipeline", "Ingestion failed"),
        ("run_transformation_pipeline", "Transformation failed"),
        ("run_aggregation_pipeline", "Aggregation failed"),
    ],
)
def test_run_full_pipeline_returns_500_when_stage_fails(
    client, mocker, failed_stage, detail
):
    mocker.patch(
        "src.api.routers.ingestion.run_ingestion_pipeline",
        return_value={"BTCUSD": 10},
    )
    mocker.patch(
        "src.api.routers.ingestion.repositories.list_enabled_symbols",
        return_value=["BTCUSD"],
    )
    mocker.patch(
        f"src.api.routers.ingestion.{failed_stage}",
        side_effect=RuntimeError("pipeline error"),
    )
    if failed_stage != "run_transformation_pipeline":
        mocker.patch(
            "src.api.routers.ingestion.run_transformation_pipeline",
            return_value={"BTCUSD": 8},
        )
    if failed_stage != "run_aggregation_pipeline":
        mocker.patch(
            "src.api.routers.ingestion.run_aggregation_pipeline",
            return_value={"BTCUSD": 2},
        )

    resp = client.post("/api/v1/ingestion/run")

    assert resp.status_code == 500
    assert resp.json()["detail"] == f"{detail}: pipeline error"


def test_latest_quote_not_found(client, mocker):
    mocker.patch(
        "src.api.routers.quotes.repositories.find_latest_quote", return_value=None
    )
    resp = client.get("/api/v1/quotes/BTCUSD/latest")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No quote found for BTCUSD"


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
    assert resp.json() == {
        "id": "q1",
        "symbol": "BTCUSD",
        "asset_type": "crypto",
        "price": "45000",
        "currency": "USD",
        "quote_date": "2024-01-01T00:00:00Z",
        "source": "coingecko",
        "processed_at": "2024-01-01T00:00:00Z",
    }


def test_quote_history(client, mocker):
    mocker.patch(
        "src.api.routers.quotes.repositories.find_quotes_by_symbol", return_value=[]
    )
    resp = client.get("/api/v1/quotes/BTCUSD/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_quote_history_returns_serialized_quotes(client, mocker):
    quote = Quote(
        id="q1",
        bronze_id="b1",
        symbol="BTCUSD",
        asset_type="crypto",
        price=Decimal("45000.50"),
        currency="USD",
        quote_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        source="coingecko",
        processed_at=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
    )
    mocker.patch(
        "src.api.routers.quotes.repositories.find_quotes_by_symbol",
        return_value=[quote],
    )

    resp = client.get("/api/v1/quotes/btcusd/history")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": "q1",
            "symbol": "BTCUSD",
            "asset_type": "crypto",
            "price": "45000.50",
            "currency": "USD",
            "quote_date": "2024-01-01T00:00:00Z",
            "source": "coingecko",
            "processed_at": "2024-01-01T01:00:00Z",
        }
    ]


def test_quote_history_forwards_date_filters(client, mocker):
    find_quotes = mocker.patch(
        "src.api.routers.quotes.repositories.find_quotes_by_symbol",
        return_value=[],
    )

    resp = client.get(
        "/api/v1/quotes/btcusd/history"
        "?start=2024-01-01T00:00:00Z&end=2024-01-31T23:59:59Z"
    )

    assert resp.status_code == 200
    find_quotes.assert_called_once_with(
        ANY,
        "BTCUSD",
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc),
    )


def test_daily_summary_returns_serialized_summary(client, mocker):
    summary = DailySummary(
        id="summary-1",
        symbol="PETR4",
        asset_type="stock",
        trade_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
        open_price=Decimal("35.10"),
        close_price=Decimal("36.20"),
        high_price=Decimal("36.50"),
        low_price=Decimal("34.90"),
        pct_change=Decimal("3.13"),
        currency="BRL",
        computed_at=datetime(2024, 1, 2, 1, tzinfo=timezone.utc),
    )
    mocker.patch(
        "src.api.routers.quotes.repositories.find_daily_summaries",
        return_value=[summary],
    )

    resp = client.get("/api/v1/quotes/petr4/summary")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": "summary-1",
            "symbol": "PETR4",
            "asset_type": "stock",
            "trade_date": "2024-01-02T00:00:00Z",
            "open_price": "35.10",
            "close_price": "36.20",
            "high_price": "36.50",
            "low_price": "34.90",
            "pct_change": "3.13",
            "currency": "BRL",
            "computed_at": "2024-01-02T01:00:00Z",
        }
    ]


def test_daily_summary_preserves_optional_null_values(client, mocker):
    summary = DailySummary(
        id="summary-1",
        symbol="PETR4",
        asset_type="stock",
        trade_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
        open_price=None,
        close_price=Decimal("36.20"),
        high_price=None,
        low_price=Decimal("34.90"),
        pct_change=None,
        currency="BRL",
    )
    mocker.patch(
        "src.api.routers.quotes.repositories.find_daily_summaries",
        return_value=[summary],
    )

    resp = client.get("/api/v1/quotes/PETR4/summary")

    assert resp.status_code == 200
    data = resp.json()[0]
    assert data["open_price"] is None
    assert data["close_price"] == "36.20"
    assert data["high_price"] is None
    assert data["low_price"] == "34.90"
    assert data["pct_change"] is None


def test_quote_history_invalid_date_range_returns_400(client):
    resp = client.get(
        "/api/v1/quotes/BTCUSD/history?start=2024-02-02T00:00:00&end=2024-01-01T00:00:00"
    )
    assert resp.status_code == 400
    assert "start" in resp.json()["detail"].lower()


def test_daily_summary_invalid_date_range_returns_400(client):
    resp = client.get(
        "/api/v1/quotes/BTCUSD/summary?start=2024-02-02T00:00:00&end=2024-01-01T00:00:00"
    )
    assert resp.status_code == 400
    assert "start" in resp.json()["detail"].lower()


def test_series_status_requires_at_least_one_symbol(client):
    resp = client.get("/api/v1/quotes/status")

    assert resp.status_code == 422


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


def test_series_status_lists_all_missing_symbols(client, mocker):
    mocker.patch(
        "src.application.status.service.repositories.find_quotes_by_symbol",
        return_value=[],
    )

    resp = client.get(
        "/api/v1/quotes/status?symbols=unknown&symbols=missing"
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "No historical series found for: UNKNOWN, MISSING"

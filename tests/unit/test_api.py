"""Unit tests for the FastAPI routes using TestClient."""
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import ANY, patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from src.api.app import create_app
from src.domain.entities.quote import Quote, DailySummary
from src.infrastructure.database.engine import get_db


def _mock_db():
    return MagicMock()


@pytest.fixture
def client():
    app = create_app()
    db = _mock_db()
    app.dependency_overrides[get_db] = lambda: db
    app.state.mock_db = db
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_live(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_ready(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok"}
    client.app.state.mock_db.execute.assert_called_once()


def test_health_ready_returns_503_when_database_is_unavailable(client):
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("connection refused")
    client.app.dependency_overrides[get_db] = lambda: db

    resp = client.get("/health/ready")

    assert resp.status_code == 503
    assert resp.json() == {"detail": "Database is unavailable"}


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
    assert resp.json()["detail"] == detail


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
    assert resp.json() == {
        "items": [],
        "limit": 100,
        "offset": 0,
        "has_next": False,
        "next_offset": None,
    }


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
    assert resp.json() == {
        "items": [{
            "id": "q1",
            "symbol": "BTCUSD",
            "asset_type": "crypto",
            "price": "45000.50",
            "currency": "USD",
            "quote_date": "2024-01-01T00:00:00Z",
            "source": "coingecko",
            "processed_at": "2024-01-01T01:00:00Z",
        }],
        "limit": 100,
        "offset": 0,
        "has_next": False,
        "next_offset": None,
    }


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
        limit=101,
        offset=0,
    )


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=1001",
        "offset=-1",
    ],
)
def test_quote_history_rejects_invalid_pagination_limits(client, mocker, query):
    find_quotes = mocker.patch(
        "src.api.routers.quotes.repositories.find_quotes_by_symbol",
        return_value=[],
    )

    resp = client.get(f"/api/v1/quotes/BTCUSD/history?{query}")

    assert resp.status_code == 422
    find_quotes.assert_not_called()

def test_quote_history_forwards_pagination(client, mocker):
    find_quotes = mocker.patch(
        "src.api.routers.quotes.repositories.find_quotes_by_symbol",
        return_value=[],
    )

    resp = client.get("/api/v1/quotes/BTCUSD/history?limit=25&offset=50")

    assert resp.status_code == 200
    find_quotes.assert_called_once_with(
        ANY, "BTCUSD", start=None, end=None, limit=26, offset=50
    )


@pytest.mark.parametrize("query", ["limit=0", "limit=1001", "offset=-1"])
def test_daily_summary_rejects_invalid_pagination_limits(client, mocker, query):
    find_summaries = mocker.patch(
        "src.api.routers.quotes.repositories.find_daily_summaries",
        return_value=[],
    )

    resp = client.get(f"/api/v1/quotes/PETR4/summary?{query}")

    assert resp.status_code == 422
    find_summaries.assert_not_called()


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
    assert resp.json() == {
        "items": [{
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
        }],
        "limit": 100,
        "offset": 0,
        "has_next": False,
        "next_offset": None,
    }


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
    data = resp.json()["items"][0]
    assert data["open_price"] is None
    assert data["close_price"] == "36.20"
    assert data["high_price"] is None
    assert data["low_price"] == "34.90"
    assert data["pct_change"] is None


def test_quote_history_returns_next_page_metadata(client, mocker):
    quotes = [
        Quote(
            id=f"q{index}",
            bronze_id=f"b{index}",
            symbol="BTCUSD",
            asset_type="crypto",
            price=Decimal(str(index)),
            currency="USD",
            quote_date=datetime(2024, 1, index, tzinfo=timezone.utc),
            source="coingecko",
            processed_at=datetime(2024, 1, index, tzinfo=timezone.utc),
        )
        for index in range(1, 4)
    ]
    find_quotes = mocker.patch(
        "src.api.routers.quotes.repositories.find_quotes_by_symbol",
        return_value=quotes,
    )

    resp = client.get("/api/v1/quotes/BTCUSD/history?limit=2&offset=4")

    assert resp.status_code == 200
    assert resp.json()["has_next"] is True
    assert resp.json()["next_offset"] == 6
    assert len(resp.json()["items"]) == 2
    find_quotes.assert_called_once_with(
        ANY, "BTCUSD", start=None, end=None, limit=3, offset=4
    )


def test_daily_summary_returns_page_metadata(client, mocker):
    mocker.patch(
        "src.api.routers.quotes.repositories.find_daily_summaries",
        return_value=[],
    )

    resp = client.get("/api/v1/quotes/PETR4/summary?limit=25&offset=50")

    assert resp.status_code == 200
    assert resp.json() == {
        "items": [],
        "limit": 25,
        "offset": 50,
        "has_next": False,
        "next_offset": None,
    }


def test_daily_summary_preserves_zero_values(client, mocker):
    summary = DailySummary(
        id="summary-1",
        symbol="PETR4",
        asset_type="stock",
        trade_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
        open_price=Decimal("0"),
        close_price=Decimal("0.00"),
        high_price=Decimal("0"),
        low_price=Decimal("0"),
        pct_change=Decimal("0"),
        currency="BRL",
    )
    mocker.patch(
        "src.api.routers.quotes.repositories.find_daily_summaries",
        return_value=[summary],
    )

    resp = client.get("/api/v1/quotes/PETR4/summary")

    assert resp.status_code == 200
    data = resp.json()["items"][0]
    assert data["open_price"] == "0"
    assert data["close_price"] == "0.00"
    assert data["high_price"] == "0"
    assert data["low_price"] == "0"
    assert data["pct_change"] == "0"


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

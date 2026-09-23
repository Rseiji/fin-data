"""Unit tests for the ingestion pipeline."""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.application.ingestion.ingest import _build_raw_quote, ingest_records
from src.infrastructure.database.repositories import save_raw_quotes


def test_build_raw_quote_basic():
    record = {
        "symbol": "BTCUSD",
        "asset_type": "crypto",
        "source": "coingecko",
        "price": 45000.0,
    }
    raw = _build_raw_quote(record)
    assert raw.symbol == "BTCUSD"
    assert raw.asset_type == "crypto"
    assert raw.source == "coingecko"
    assert json.loads(raw.raw_payload) == record
    assert isinstance(raw.id, str)
    assert len(raw.id) == 36  # UUID4


def test_ingest_records_calls_save(mocker):
    mock_db = MagicMock()
    mock_save = mocker.patch(
        "src.application.ingestion.ingest.repositories.save_raw_quote"
    )
    records = [
        {"symbol": "BTCUSD", "asset_type": "crypto", "source": "coingecko", "price": 45000},
        {"symbol": "ETHUSD", "asset_type": "crypto", "source": "coingecko", "price": 3000},
    ]
    count = ingest_records(mock_db, records)
    assert count == 2
    assert mock_save.call_count == 2


def test_ingest_records_handles_error(mocker):
    mock_db = MagicMock()
    mocker.patch(
        "src.application.ingestion.ingest.repositories.save_raw_quotes",
        side_effect=Exception("DB error"),
    )
    records = [{"symbol": "BTCUSD", "asset_type": "crypto", "source": "coingecko", "price": 45000}]
    count = ingest_records(mock_db, records)
    assert count == 0


def test_save_raw_quotes_batches_commits():
    mock_db = MagicMock()
    raw_quotes = [
        _build_raw_quote({"symbol": "BTCUSD", "asset_type": "crypto", "source": "coingecko", "price": 45000}),
        _build_raw_quote({"symbol": "ETHUSD", "asset_type": "crypto", "source": "coingecko", "price": 3000}),
    ]

    count = save_raw_quotes(mock_db, raw_quotes, batch_size=1)

    assert count == 2
    assert mock_db.merge.call_count == 2
    assert mock_db.commit.call_count == 2

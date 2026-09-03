"""Unit tests for the scrapers (network calls mocked)."""
import json
import pytest
import responses as resp_lib

from src.infrastructure.scrapers import crypto, currencies, indexes
from src.infrastructure.database.models import AssetType, TrackedAsset


def _asset(symbol, asset_type, provider_symbol, provider_config=None, source="test"):
    return TrackedAsset(
        symbol=symbol,
        asset_type=asset_type,
        source=source,
        provider_symbol=provider_symbol,
        provider_config=provider_config or {},
    )


@resp_lib.activate
def test_scrape_crypto_prices():
    mock_response = {
        "bitcoin": {"usd": 45000.0, "usd_24h_change": 1.5, "last_updated_at": 1700000000},
        "ethereum": {"usd": 3000.0, "usd_24h_change": -0.5, "last_updated_at": 1700000000},
    }
    resp_lib.add(
        resp_lib.GET,
        "https://api.coingecko.com/api/v3/simple/price",
        json=mock_response,
        status=200,
    )
    results = crypto.scrape_crypto_prices(assets=[
        _asset("BTCUSD", AssetType.crypto, "bitcoin", {"vs_currency": "usd"}, "coingecko"),
        _asset("ETHUSD", AssetType.crypto, "ethereum", {"vs_currency": "usd"}, "coingecko"),
    ])
    assert len(results) == 2
    symbols = {r["symbol"] for r in results}
    assert "BTCUSD" in symbols
    assert "ETHUSD" in symbols
    btc = next(r for r in results if r["symbol"] == "BTCUSD")
    assert btc["price"] == 45000.0


@resp_lib.activate
def test_scrape_crypto_prices_skips_failed_historical_asset():
    resp_lib.add(
        resp_lib.GET,
        "https://api.coingecko.com/api/v3/coins/ethena/market_chart",
        status=429,
    )
    resp_lib.add(
        resp_lib.GET,
        "https://api.coingecko.com/api/v3/coins/aave/market_chart",
        json={"prices": [[1700000000000, 100.0]]},
        status=200,
    )

    results = crypto.scrape_crypto_prices(
        assets=[
            _asset("ENA", AssetType.crypto, "ethena"),
            _asset("AAVE", AssetType.crypto, "aave"),
        ],
        lookback_days=6,
    )

    assert [result["symbol"] for result in results] == ["AAVE"]


@resp_lib.activate
def test_scrape_bcb_series():
    mock_response = [{"data": "01/08/2024", "valor": "10.50"}]
    resp_lib.add(
        resp_lib.GET,
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1",
        json=mock_response,
        status=200,
    )
    results = indexes.scrape_bcb_series(
        "SELIC", last_n=1, asset=_asset("SELIC", AssetType.index, "432", source="bcb")
    )
    assert len(results) == 1
    assert results[0]["symbol"] == "SELIC"
    assert results[0]["value"] == "10.50"


@resp_lib.activate
def test_scrape_currency_pair():
    mock_response = {
        "rates": {"BRL": 5.0},
        "time_last_update_utc": "Mon, 01 Jan 2024 00:00:00 +0000",
    }
    resp_lib.add(
        resp_lib.GET,
        "https://open.er-api.com/v6/latest/USD",
        json=mock_response,
        status=200,
    )
    result = currencies.scrape_currency_pair(
        _asset("USDBRL", AssetType.currency, "USD/BRL", {"base": "USD", "quote": "BRL"})
    )
    assert result["symbol"] == "USDBRL"
    assert result["price"] == 5.0
    assert result["currency"] == "BRL"


@resp_lib.activate
def test_scrape_currencies_broadcasts_same_base_in_one_call():
    mock_response = {
        "rates": {"BRL": 5.0, "EUR": 0.92},
        "time_last_update_utc": "Mon, 01 Jan 2024 00:00:00 +0000",
    }
    resp_lib.add(
        resp_lib.GET,
        "https://open.er-api.com/v6/latest/USD",
        json=mock_response,
        status=200,
    )

    results = currencies.scrape_currencies(assets=[
        _asset("USDBRL", AssetType.currency, "USD/BRL", {"base": "USD", "quote": "BRL"}),
        _asset("USDEUR", AssetType.currency, "USD/EUR", {"base": "USD", "quote": "EUR"}),
    ])

    assert len(results) == 2
    assert len(resp_lib.calls) == 1
    assert {r["symbol"] for r in results} == {"USDBRL", "USDEUR"}


def test_scrape_unknown_currency_pair():
    with pytest.raises(KeyError):
        currencies.scrape_currency_pair(
            _asset("INVALID", AssetType.currency, "INVALID", {})
        )


def test_registry_resolves_scrapers_by_category():
    from src.infrastructure.scrapers.registry import get_scraper, list_scrapers

    scraper_names = list_scrapers()
    assert {"stocks", "etfs", "crypto", "currency", "index"}.issubset(set(scraper_names))

    for scraper_name in scraper_names:
        scraper = get_scraper(scraper_name)
        assert scraper is not None
        assert hasattr(scraper, "fetch_all")
        assert hasattr(scraper, "fetch_history")

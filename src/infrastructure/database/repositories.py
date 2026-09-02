"""SQLAlchemy-backed repository implementations."""
import json
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.entities.quote import DailySummary, Quote, RawQuote
from src.infrastructure.database import models


def list_enabled_assets(db: Session, asset_type: Optional[str] = None) -> List[models.TrackedAsset]:
    query = db.query(models.TrackedAsset).filter(models.TrackedAsset.enabled.is_(True))
    if asset_type is not None:
        query = query.filter(models.TrackedAsset.asset_type == asset_type)
    return query.order_by(models.TrackedAsset.symbol).all()


def list_enabled_symbols(db: Session, asset_type: Optional[str] = None) -> List[str]:
    return [asset.symbol for asset in list_enabled_assets(db, asset_type)]


def ensure_default_tracked_assets(db: Session) -> None:
    defaults = [
        *[(symbol, models.AssetType.stock, "yahoo_finance", f"{symbol}.SA", {}) for symbol in (
            "PETR4", "ITUB4", "SAPR11", "CEAB3", "VALE3", "BBAS3", "WEGE3", "RENT3"
        )],
        *[(symbol, models.AssetType.etf, "yahoo_finance", f"{symbol}.SA", {}) for symbol in (
            "IVVB11", "BOVA11", "DIVO11", "SMAL11", "XFIX11"
        )],
        ("BTCUSD", models.AssetType.crypto, "coingecko", "bitcoin", {"vs_currency": "usd"}),
        ("ETHUSD", models.AssetType.crypto, "coingecko", "ethereum", {"vs_currency": "usd"}),
        ("BNBUSD", models.AssetType.crypto, "coingecko", "binancecoin", {"vs_currency": "usd"}),
        ("SOLUSD", models.AssetType.crypto, "coingecko", "solana", {"vs_currency": "usd"}),
        ("ADAUSD", models.AssetType.crypto, "coingecko", "cardano", {"vs_currency": "usd"}),
        ("ENA", models.AssetType.crypto, "coingecko", "ethena", {"vs_currency": "usd"}),
        ("HYPE", models.AssetType.crypto, "coingecko", "hyperliquid", {"vs_currency": "usd"}),
        ("AAVE", models.AssetType.crypto, "coingecko", "aave", {"vs_currency": "usd"}),
        ("SUI", models.AssetType.crypto, "coingecko", "sui", {"vs_currency": "usd"}),
        ("GS", models.AssetType.crypto, "coingecko", "gammaswap", {"vs_currency": "usd"}),
        ("ALGN", models.AssetType.crypto, "coingecko", "aligned", {"vs_currency": "usd"}),
        ("LINK", models.AssetType.crypto, "coingecko", "chainlink", {"vs_currency": "usd"}),
        ("NEAR", models.AssetType.crypto, "coingecko", "near", {"vs_currency": "usd"}),
        ("PENDLE", models.AssetType.crypto, "coingecko", "pendle", {"vs_currency": "usd"}),
        ("SYRUP", models.AssetType.crypto, "coingecko", "syrup", {"vs_currency": "usd"}),
        ("SPECTRA", models.AssetType.crypto, "coingecko", "spectra-finance", {"vs_currency": "usd"}),
        ("USDBRL", models.AssetType.currency, "open_er_api", "USD/BRL", {"base": "USD", "quote": "BRL"}),
        ("JPYBRL", models.AssetType.currency, "open_er_api", "JPY/BRL", {"base": "JPY", "quote": "BRL"}),
        ("USDEUR", models.AssetType.currency, "open_er_api", "USD/EUR", {"base": "USD", "quote": "EUR"}),
        ("EURUSD", models.AssetType.currency, "open_er_api", "EUR/USD", {"base": "EUR", "quote": "USD"}),
        ("GBPBRL", models.AssetType.currency, "open_er_api", "GBP/BRL", {"base": "GBP", "quote": "BRL"}),
        ("SELIC", models.AssetType.index, "bcb", "432", {}),
        ("CDI", models.AssetType.index, "bcb", "12", {}),
        ("IPCA", models.AssetType.index, "bcb", "433", {}),
        ("IFIX", models.AssetType.index, "bcb", "12472", {}),
    ]
    for symbol, asset_type, source, provider_symbol, provider_config in defaults:
        asset = db.query(models.TrackedAsset).filter_by(symbol=symbol).one_or_none()
        if asset is None:
            asset = models.TrackedAsset(symbol=symbol)
            db.add(asset)
        asset.asset_type = asset_type
        asset.source = source
        asset.provider_symbol = provider_symbol
        asset.provider_config = provider_config
    db.commit()


def save_raw_quote(db: Session, raw_quote: RawQuote) -> None:
    record = models.BronzeQuote(
        id=raw_quote.id,
        symbol=raw_quote.symbol,
        asset_type=raw_quote.asset_type,
        source=raw_quote.source,
        raw_payload=raw_quote.raw_payload,
        ingested_at=raw_quote.ingested_at,
    )
    db.merge(record)
    db.commit()


def find_raw_quotes_by_symbol(
    db: Session, symbol: str, limit: int = 100
) -> List[RawQuote]:
    rows = (
        db.query(models.BronzeQuote)
        .filter(models.BronzeQuote.symbol == symbol)
        .order_by(models.BronzeQuote.ingested_at.desc())
        .limit(limit)
        .all()
    )
    return [
        RawQuote(
            id=r.id,
            symbol=r.symbol,
            asset_type=r.asset_type.value,
            source=r.source,
            raw_payload=r.raw_payload,
            ingested_at=r.ingested_at,
        )
        for r in rows
    ]


def save_quote(db: Session, quote: Quote) -> None:
    record = db.query(models.SilverQuote).filter_by(
        symbol=quote.symbol, quote_date=quote.quote_date, source=quote.source
    ).one_or_none()
    if record is None:
        record = models.SilverQuote(id=quote.id)
        db.add(record)
    record.bronze_id = quote.bronze_id
    record.symbol = quote.symbol
    record.asset_type = quote.asset_type
    record.price = quote.price
    record.currency = quote.currency
    record.quote_date = quote.quote_date
    record.source = quote.source
    record.processed_at = quote.processed_at
    db.commit()


def find_quotes_by_symbol(
    db: Session,
    symbol: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[Quote]:
    q = db.query(models.SilverQuote).filter(models.SilverQuote.symbol == symbol)
    if start:
        q = q.filter(models.SilverQuote.quote_date >= start)
    if end:
        q = q.filter(models.SilverQuote.quote_date <= end)
    rows = q.order_by(models.SilverQuote.quote_date.desc()).all()
    return [
        Quote(
            id=r.id,
            bronze_id=r.bronze_id,
            symbol=r.symbol,
            asset_type=r.asset_type.value,
            price=Decimal(str(r.price)),
            currency=r.currency,
            quote_date=r.quote_date,
            source=r.source,
            processed_at=r.processed_at,
        )
        for r in rows
    ]


def find_latest_quote(db: Session, symbol: str) -> Optional[Quote]:
    row = (
        db.query(models.SilverQuote)
        .filter(models.SilverQuote.symbol == symbol)
        .order_by(models.SilverQuote.quote_date.desc())
        .first()
    )
    if not row:
        return None
    return Quote(
        id=row.id,
        bronze_id=row.bronze_id,
        symbol=row.symbol,
        asset_type=row.asset_type.value,
        price=Decimal(str(row.price)),
        currency=row.currency,
        quote_date=row.quote_date,
        source=row.source,
        processed_at=row.processed_at,
    )


def save_daily_summary(db: Session, summary: DailySummary) -> None:
    record = db.query(models.GoldDailySummary).filter_by(
        symbol=summary.symbol, trade_date=summary.trade_date
    ).one_or_none()
    if record is None:
        record = models.GoldDailySummary(id=summary.id)
        db.add(record)
    record.symbol = summary.symbol
    record.asset_type = summary.asset_type
    record.trade_date = summary.trade_date
    record.open_price = summary.open_price
    record.close_price = summary.close_price
    record.high_price = summary.high_price
    record.low_price = summary.low_price
    record.pct_change = summary.pct_change
    record.currency = summary.currency
    record.computed_at = summary.computed_at
    db.commit()


def find_daily_summaries(
    db: Session,
    symbol: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[DailySummary]:
    q = db.query(models.GoldDailySummary).filter(
        models.GoldDailySummary.symbol == symbol
    )
    if start:
        q = q.filter(models.GoldDailySummary.trade_date >= start)
    if end:
        q = q.filter(models.GoldDailySummary.trade_date <= end)
    rows = q.order_by(models.GoldDailySummary.trade_date.desc()).all()
    return [
        DailySummary(
            id=r.id,
            symbol=r.symbol,
            asset_type=r.asset_type.value,
            trade_date=r.trade_date,
            open_price=Decimal(str(r.open_price)) if r.open_price else None,
            close_price=Decimal(str(r.close_price)) if r.close_price else None,
            high_price=Decimal(str(r.high_price)) if r.high_price else None,
            low_price=Decimal(str(r.low_price)) if r.low_price else None,
            pct_change=Decimal(str(r.pct_change)) if r.pct_change else None,
            currency=r.currency,
            computed_at=r.computed_at,
        )
        for r in rows
    ]

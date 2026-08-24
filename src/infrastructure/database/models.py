import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    Text,
    Enum,
    UniqueConstraint,
    Index,
    func,
)

from src.infrastructure.database.engine import Base


class AssetType(str, enum.Enum):
    crypto = "crypto"
    stock = "stock"
    etf = "etf"
    index = "index"
    currency = "currency"


class Layer(str, enum.Enum):
    bronze = "bronze"
    silver = "silver"
    gold = "gold"


# ---------------------------------------------------------------------------
# Bronze layer – raw ingested data
# ---------------------------------------------------------------------------

class BronzeQuote(Base):
    __tablename__ = "bronze_quotes"

    id = Column(String(36), primary_key=True)
    symbol = Column(String(32), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    source = Column(String(64), nullable=False)
    raw_payload = Column(Text, nullable=False)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_bronze_symbol_ingested", "symbol", "ingested_at"),
    )


# ---------------------------------------------------------------------------
# Silver layer – cleaned and validated data
# ---------------------------------------------------------------------------

class SilverQuote(Base):
    __tablename__ = "silver_quotes"

    id = Column(String(36), primary_key=True)
    bronze_id = Column(String(36), nullable=False)
    symbol = Column(String(32), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    price = Column(Numeric(24, 8), nullable=False)
    currency = Column(String(8), nullable=False)
    quote_date = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(64), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "quote_date", "source", name="uq_silver_symbol_date_source"),
        Index("ix_silver_symbol_date", "symbol", "quote_date"),
    )


# ---------------------------------------------------------------------------
# Gold layer – aggregated / enriched data
# ---------------------------------------------------------------------------

class GoldDailySummary(Base):
    __tablename__ = "gold_daily_summaries"

    id = Column(String(36), primary_key=True)
    symbol = Column(String(32), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    trade_date = Column(DateTime(timezone=True), nullable=False)
    open_price = Column(Numeric(24, 8))
    close_price = Column(Numeric(24, 8))
    high_price = Column(Numeric(24, 8))
    low_price = Column(Numeric(24, 8))
    pct_change = Column(Numeric(10, 6))
    currency = Column(String(8), nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_gold_symbol_trade_date"),
        Index("ix_gold_symbol_date", "symbol", "trade_date"),
    )

"""Quote endpoints – latest price, historical series, daily summaries."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.application.status.service import get_series_status
from src.infrastructure.database.engine import get_db
from src.infrastructure.database import repositories

router = APIRouter(prefix="/quotes", tags=["quotes"])


class QuoteOut(BaseModel):
    id: str
    symbol: str
    asset_type: str
    price: str
    currency: str
    quote_date: datetime
    source: str
    processed_at: datetime

    model_config = {"from_attributes": True}


class DailySummaryOut(BaseModel):
    id: str
    symbol: str
    asset_type: str
    trade_date: datetime
    open_price: Optional[str]
    close_price: Optional[str]
    high_price: Optional[str]
    low_price: Optional[str]
    pct_change: Optional[str]
    currency: str
    computed_at: datetime

    model_config = {"from_attributes": True}


class SeriesStatusOut(BaseModel):
    symbol: str
    start_date: datetime
    last_date: datetime
    last_price: str
    first_price: str
    variance: str
    standard_deviation: str
    mean: str
    granularity: str
    record_count: int


@router.get("/status", response_model=List[SeriesStatusOut])
def get_series_statuses(
    symbols: List[str] = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    statuses = []
    missing = []
    for symbol in symbols:
        status = get_series_status(db, symbol)
        if status is None:
            missing.append(symbol.upper())
            continue
        statuses.append(
            SeriesStatusOut(
                symbol=status.symbol,
                start_date=status.start_date,
                last_date=status.last_date,
                last_price=str(status.last_price),
                first_price=str(status.first_price),
                variance=str(status.variance),
                standard_deviation=str(status.standard_deviation),
                mean=str(status.mean),
                granularity=status.granularity,
                record_count=status.record_count,
            )
        )
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"No historical series found for: {', '.join(missing)}",
        )
    return statuses


@router.get("/{symbol}/latest", response_model=QuoteOut)
def get_latest_quote(symbol: str, db: Session = Depends(get_db)):
    quote = repositories.find_latest_quote(db, symbol.upper())
    if quote is None:
        raise HTTPException(status_code=404, detail=f"No quote found for {symbol}")
    return QuoteOut(
        id=quote.id,
        symbol=quote.symbol,
        asset_type=quote.asset_type,
        price=str(quote.price),
        currency=quote.currency,
        quote_date=quote.quote_date,
        source=quote.source,
        processed_at=quote.processed_at,
    )


@router.get("/{symbol}/history", response_model=List[QuoteOut])
def get_quote_history(
    symbol: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    quotes = repositories.find_quotes_by_symbol(db, symbol.upper(), start=start, end=end)
    return [
        QuoteOut(
            id=q.id,
            symbol=q.symbol,
            asset_type=q.asset_type,
            price=str(q.price),
            currency=q.currency,
            quote_date=q.quote_date,
            source=q.source,
            processed_at=q.processed_at,
        )
        for q in quotes
    ]


@router.get("/{symbol}/summary", response_model=List[DailySummaryOut])
def get_daily_summary(
    symbol: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    summaries = repositories.find_daily_summaries(db, symbol.upper(), start=start, end=end)
    return [
        DailySummaryOut(
            id=s.id,
            symbol=s.symbol,
            asset_type=s.asset_type,
            trade_date=s.trade_date,
            open_price=str(s.open_price) if s.open_price else None,
            close_price=str(s.close_price) if s.close_price else None,
            high_price=str(s.high_price) if s.high_price else None,
            low_price=str(s.low_price) if s.low_price else None,
            pct_change=str(s.pct_change) if s.pct_change else None,
            currency=s.currency,
            computed_at=s.computed_at,
        )
        for s in summaries
    ]

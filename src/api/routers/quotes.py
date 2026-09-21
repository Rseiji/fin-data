"""Quote endpoints – latest price, historical series, daily summaries."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.application.status.service import get_series_status
from src.infrastructure.database.engine import get_db
from src.infrastructure.database import repositories

router = APIRouter(prefix="/quotes", tags=["quotes"])


def _validate_date_range(start: Optional[datetime], end: Optional[datetime]) -> None:
    if start and end and start > end:
        raise HTTPException(
            status_code=400,
            detail="start date must be earlier than or equal to end date",
        )


class QuoteOut(BaseModel):
    id: str = Field(description="Unique identifier of the processed quote.")
    symbol: str = Field(description="Asset symbol, such as BTCUSD or PETR4.")
    asset_type: str = Field(description="Category of the asset.")
    price: str = Field(description="Quote price represented as a decimal string.")
    currency: str = Field(description="Currency in which the quote is expressed.")
    quote_date: datetime = Field(description="Date and time associated with the quote.")
    source: str = Field(description="External source that provided the quote.")
    processed_at: datetime = Field(description="Date and time when the quote was processed.")

    model_config = {"from_attributes": True}


class DailySummaryOut(BaseModel):
    id: str = Field(description="Unique identifier of the daily summary.")
    symbol: str = Field(description="Asset symbol, such as BTCUSD or PETR4.")
    asset_type: str = Field(description="Category of the asset.")
    trade_date: datetime = Field(description="Trading date represented by the summary.")
    open_price: Optional[str] = Field(description="Opening price as a decimal string.")
    close_price: Optional[str] = Field(description="Closing price as a decimal string.")
    high_price: Optional[str] = Field(description="Highest price as a decimal string.")
    low_price: Optional[str] = Field(description="Lowest price as a decimal string.")
    pct_change: Optional[str] = Field(
        description="Percentage change as a decimal string."
    )
    currency: str = Field(description="Currency in which the summary is expressed.")
    computed_at: datetime = Field(description="Date and time when the summary was computed.")

    model_config = {"from_attributes": True}


class SeriesStatusOut(BaseModel):
    symbol: str = Field(description="Asset symbol represented by the series.")
    start_date: datetime = Field(description="Date of the first record in the series.")
    last_date: datetime = Field(description="Date of the latest record in the series.")
    last_price: str = Field(description="Latest price as a decimal string.")
    first_price: str = Field(description="First price as a decimal string.")
    variance: str = Field(description="Sample variance as a decimal string.")
    standard_deviation: str = Field(
        description="Sample standard deviation as a decimal string."
    )
    mean: str = Field(description="Arithmetic mean as a decimal string.")
    granularity: str = Field(description="Inferred periodicity of the series.")
    record_count: int = Field(description="Number of records in the series.")


@router.get(
    "/status",
    response_model=List[SeriesStatusOut],
    summary="Get historical series status",
    description=(
        "Returns statistical metadata for each requested symbol, "
        "preserving the order provided in the query string."
    ),
    responses={
        404: {
            "description": "No historical series was found for one or more symbols."
        },
    },
)
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


@router.get(
    "/{symbol}/latest",
    response_model=QuoteOut,
    summary="Get the latest quote",
    description="Returns the most recent processed quote for the requested symbol.",
    responses={
        404: {"description": "No quote was found for the requested symbol."},
    },
)
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


@router.get(
    "/{symbol}/history",
    response_model=List[QuoteOut],
    summary="Get quote history",
    description=(
        "Returns the historical quotes for a symbol, optionally filtered "
        "by a start and end datetime."
    ),
    responses={
        400: {"description": "The start datetime is later than the end datetime."},
    },
)
def get_quote_history(
    symbol: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    _validate_date_range(start, end)
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


@router.get(
    "/{symbol}/summary",
    response_model=List[DailySummaryOut],
    summary="Get daily quote summaries",
    description=(
        "Returns daily OHLC summaries for a symbol, optionally filtered "
        "by a start and end datetime."
    ),
    responses={
        400: {"description": "The start datetime is later than the end datetime."},
    },
)
def get_daily_summary(
    symbol: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    _validate_date_range(start, end)
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

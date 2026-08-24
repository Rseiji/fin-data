"""Ingestion endpoints – trigger data collection and transformation manually."""
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.infrastructure.database.engine import get_db
from src.application.ingestion.ingest import run_ingestion_pipeline
from src.application.transformation.transform import run_transformation_pipeline
from src.application.aggregation.aggregate import run_aggregation_pipeline
from src.infrastructure.scrapers.stocks import STOCK_SYMBOLS, ETF_SYMBOLS
from src.infrastructure.scrapers.crypto import CRYPTO_SYMBOLS
from src.infrastructure.scrapers.currencies import CURRENCY_PAIRS
from src.infrastructure.scrapers.indexes import BCB_CODES

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class IngestionResult(BaseModel):
    ingested: Dict[str, int]
    transformed: Dict[str, int]
    aggregated: Dict[str, int]


@router.post("/run", response_model=IngestionResult)
def run_full_pipeline(db: Session = Depends(get_db)):
    """Trigger the full ingestion → transformation → aggregation pipeline."""
    try:
        ingested = run_ingestion_pipeline(db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    all_symbols = (
        list(STOCK_SYMBOLS)
        + list(ETF_SYMBOLS)
        + list(CRYPTO_SYMBOLS.keys())
        + list(CURRENCY_PAIRS.keys())
        + list(BCB_CODES.keys())
    )

    try:
        transformed = run_transformation_pipeline(db, all_symbols)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transformation failed: {exc}") from exc

    try:
        aggregated = run_aggregation_pipeline(db, all_symbols)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {exc}") from exc

    return IngestionResult(
        ingested=ingested, transformed=transformed, aggregated=aggregated
    )

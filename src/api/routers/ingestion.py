"""Ingestion endpoints – trigger data collection and transformation manually."""
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.infrastructure.database.engine import get_db
from src.application.ingestion.ingest import run_ingestion_pipeline
from src.application.transformation.transform import run_transformation_pipeline
from src.application.aggregation.aggregate import run_aggregation_pipeline
from src.infrastructure.database import repositories

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
logger = logging.getLogger(__name__)


class IngestionResult(BaseModel):
    ingested: Dict[str, int] = Field(
        description="Number of records ingested for each symbol."
    )
    transformed: Dict[str, int] = Field(
        description="Number of records transformed for each symbol."
    )
    aggregated: Dict[str, int] = Field(
        description="Number of daily summaries aggregated for each symbol."
    )


@router.post(
    "/run",
    response_model=IngestionResult,
    summary="Run the full ingestion pipeline",
    description=(
        "Triggers ingestion, transformation, and aggregation "
        "for all enabled symbols."
    ),
    responses={
        500: {"description": "A pipeline stage failed during execution."},
    },
)
def run_full_pipeline(db: Session = Depends(get_db)):
    """Trigger the full ingestion → transformation → aggregation pipeline."""
    try:
        ingested = run_ingestion_pipeline(db)
    except Exception as exc:
        logger.exception("Ingestion stage failed")
        raise HTTPException(status_code=500, detail="Ingestion failed") from exc

    all_symbols = (
        repositories.list_enabled_symbols(db)
    )

    try:
        transformed = run_transformation_pipeline(db, all_symbols)
    except Exception as exc:
        logger.exception("Transformation stage failed")
        raise HTTPException(status_code=500, detail="Transformation failed") from exc

    try:
        aggregated = run_aggregation_pipeline(db, all_symbols)
    except Exception as exc:
        logger.exception("Aggregation stage failed")
        raise HTTPException(status_code=500, detail="Aggregation failed") from exc

    return IngestionResult(
        ingested=ingested, transformed=transformed, aggregated=aggregated
    )

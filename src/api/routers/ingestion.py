"""Ingestion endpoints – trigger data collection and transformation manually."""
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.infrastructure.database.engine import get_db
from src.application.ingestion.ingest import run_ingestion_pipeline
from src.application.transformation.transform import run_transformation_pipeline
from src.application.aggregation.aggregate import run_aggregation_pipeline
from src.application.ingestion.jobs import IngestionJob, IngestionJobManager
from src.infrastructure.database import repositories

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
logger = logging.getLogger(__name__)


class PipelineStageError(RuntimeError):
    def __init__(self, stage: str, cause: Exception):
        super().__init__(stage)
        self.stage = stage
        self.__cause__ = cause


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


class IngestionRunOut(BaseModel):
    run_id: str
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: IngestionResult | None = None
    error: str | None = None


def _serialize_job(job: IngestionJob) -> IngestionRunOut:
    result = IngestionResult(**job.result) if job.result is not None else None
    return IngestionRunOut(
        run_id=job.id,
        status=job.status,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        result=result,
        error=job.error,
    )


def _get_ingestion_manager(request: Request) -> IngestionJobManager:
    return request.app.state.ingestion_manager


def _execute_pipeline(db: Session) -> Dict[str, Dict[str, int]]:
    """Execute every pipeline stage using a session owned by the caller."""
    try:
        ingested = run_ingestion_pipeline(db)
    except Exception as exc:
        raise PipelineStageError("Ingestion", exc) from exc
    all_symbols = repositories.list_enabled_symbols(db)
    try:
        transformed = run_transformation_pipeline(db, all_symbols)
    except Exception as exc:
        raise PipelineStageError("Transformation", exc) from exc
    try:
        aggregated = run_aggregation_pipeline(db, all_symbols)
    except Exception as exc:
        raise PipelineStageError("Aggregation", exc) from exc
    return {
        "ingested": ingested,
        "transformed": transformed,
        "aggregated": aggregated,
    }


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
        result = _execute_pipeline(db)
    except PipelineStageError as exc:
        logger.exception("Synchronous ingestion failed at %s stage", exc.stage)
        raise HTTPException(status_code=500, detail=f"{exc.stage} failed") from exc
    except Exception as exc:
        logger.exception("Synchronous ingestion failed")
        raise HTTPException(status_code=500, detail="Ingestion failed") from exc
    return IngestionResult(**result)


@router.post(
    "/runs",
    response_model=IngestionRunOut,
    status_code=202,
    summary="Start an asynchronous ingestion run",
    description="Queues the full ingestion pipeline and returns its tracking id.",
)
def start_ingestion_run(
    manager: IngestionJobManager = Depends(_get_ingestion_manager),
):
    return _serialize_job(manager.submit())


@router.get(
    "/runs/{run_id}",
    response_model=IngestionRunOut,
    summary="Get ingestion run status",
)
def get_ingestion_run(
    run_id: str,
    manager: IngestionJobManager = Depends(_get_ingestion_manager),
):
    job = manager.get(run_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    return _serialize_job(job)

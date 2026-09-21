"""In-memory asynchronous execution tracking for ingestion jobs."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from src.infrastructure.database.engine import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class IngestionJob:
    id: str
    status: str = "queued"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class IngestionJobManager:
    """Submit ingestion work without tying a database session to a request."""

    def __init__(self, pipeline: Callable[[Session], Dict[str, Any]]) -> None:
        self._pipeline = pipeline
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingestion")
        self._jobs: Dict[str, IngestionJob] = {}
        self._lock = Lock()

    def submit(self) -> IngestionJob:
        job = IngestionJob(id=str(uuid4()))
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run, job.id)
        return job

    def get(self, job_id: str) -> Optional[IngestionJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)

        db = SessionLocal()
        try:
            result = self._pipeline(db)
        except Exception:
            logger.exception("Asynchronous ingestion failed: run_id=%s", job_id)
            with self._lock:
                job.status = "failed"
                job.error = "Ingestion failed"
                job.finished_at = datetime.now(timezone.utc)
        else:
            with self._lock:
                job.status = "succeeded"
                job.result = result
                job.finished_at = datetime.now(timezone.utc)
        finally:
            db.close()

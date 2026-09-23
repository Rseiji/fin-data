from threading import Event
from time import monotonic

from src.application.ingestion.jobs import IngestionJobManager


def test_manager_runs_pipeline_in_background_and_tracks_status(mocker):
    started = Event()
    release = Event()
    finished = Event()
    db = object()
    mocker.patch("src.application.ingestion.jobs.SessionLocal", return_value=db)

    def pipeline(received_db):
        assert received_db is db
        started.set()
        release.wait(timeout=1)
        finished.set()
        return {
            "ingested": {"BTCUSD": 1},
            "transformed": {"BTCUSD": 1},
            "aggregated": {"BTCUSD": 1},
        }

    manager = IngestionJobManager(pipeline)
    try:
        job = manager.submit()
        assert started.wait(timeout=1)
        assert manager.get(job.id).status == "running"

        release.set()
        assert finished.wait(timeout=1)
        assert manager.get(job.id).status == "succeeded"
        assert manager.get(job.id).result["aggregated"] == {"BTCUSD": 1}
    finally:
        manager.shutdown()


def test_manager_records_failed_pipeline(mocker):
    mocker.patch("src.application.ingestion.jobs.SessionLocal", return_value=object())
    finished = Event()

    def pipeline(_db):
        finished.set()
        raise RuntimeError("provider unavailable")

    manager = IngestionJobManager(pipeline)
    try:
        job = manager.submit()
        assert finished.wait(timeout=1)
        deadline = monotonic() + 1
        while manager.get(job.id).status == "running" and monotonic() < deadline:
            finished.wait(timeout=0.01)
        assert manager.get(job.id).status == "failed"
        assert manager.get(job.id).error == "Ingestion failed"
    finally:
        manager.shutdown()

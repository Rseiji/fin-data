"""FastAPI application factory."""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.routers import quotes, ingestion
from src.api.routers.auth import get_current_user, router as auth_router
from src.application.ingestion.jobs import IngestionJobManager
from src.infrastructure.database.engine import create_all_tables, get_db
from src.config.settings import settings

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables if not present…")
    create_all_tables()
    logger.info("fin-data API started (env=%s)", settings.app_env)
    yield
    app.state.ingestion_manager.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="fin-data API",
        description=(
            "Financial data API providing prices for cryptocurrencies, "
            "Brazilian stocks, ETFs, macro-economic indexes and currency pairs."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(quotes.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
    app.include_router(ingestion.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
    app.state.ingestion_manager = IngestionJobManager(ingestion._execute_pipeline)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    @app.get("/health/live", tags=["health"])
    def health_live():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def health_ready(db: Session = Depends(get_db)):
        try:
            db.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            logger.warning("Readiness check failed: %s", exc)
            raise HTTPException(status_code=503, detail="Database is unavailable") from exc
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()

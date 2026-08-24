"""FastAPI application factory."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routers import quotes, ingestion
from src.infrastructure.database.engine import create_all_tables
from src.config.settings import settings

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables if not present…")
    create_all_tables()
    logger.info("fin-data API started (env=%s)", settings.app_env)
    yield


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

    app.include_router(quotes.router, prefix="/api/v1")
    app.include_router(ingestion.router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()

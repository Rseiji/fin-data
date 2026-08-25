"""APScheduler-based orchestration for automatic data ingestion."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import settings
from src.infrastructure.database.engine import SessionLocal
from src.infrastructure.database import repositories

logger = logging.getLogger(__name__)


def _get_all_symbols():
    db = SessionLocal()
    try:
        tracked_symbols = repositories.list_enabled_symbols(db)
    finally:
        db.close()
    return (
        tracked_symbols
    )


def _run_stocks_pipeline():
    """Ingest only Brazilian stocks and ETFs (runs on market hours)."""
    from src.infrastructure.scrapers import stocks
    from src.application.ingestion.ingest import ingest_records
    from src.application.transformation.transform import run_transformation_pipeline
    from src.application.aggregation.aggregate import run_aggregation_pipeline

    logger.info("Stocks/ETF pipeline starting…")
    db = SessionLocal()
    try:
        stock_assets = repositories.list_enabled_assets(db, "stock")
        etf_assets = repositories.list_enabled_assets(db, "etf")
        records = stocks.scrape_stocks(stock_assets) + stocks.scrape_etfs(etf_assets)
        ingest_records(db, records)
        symbols = [asset.symbol for asset in stock_assets + etf_assets]
        run_transformation_pipeline(db, symbols)
        run_aggregation_pipeline(db, symbols)
        logger.info("Stocks/ETF pipeline completed")
    except Exception as exc:
        logger.error("Stocks/ETF pipeline failed: %s", exc)
    finally:
        db.close()


def _run_crypto_currency_pipeline():
    """Ingest crypto prices and currency pairs (runs hourly)."""
    from src.infrastructure.scrapers import crypto, currencies, indexes
    from src.application.ingestion.ingest import ingest_records
    from src.application.transformation.transform import run_transformation_pipeline
    from src.application.aggregation.aggregate import run_aggregation_pipeline

    logger.info("Crypto/currency pipeline starting…")
    db = SessionLocal()
    try:
        crypto_assets = repositories.list_enabled_assets(db, "crypto")
        currency_assets = repositories.list_enabled_assets(db, "currency")
        index_assets = repositories.list_enabled_assets(db, "index")
        records = (
            crypto.scrape_crypto_prices(assets=crypto_assets)
            + currencies.scrape_currencies(assets=currency_assets)
            + indexes.scrape_all_indexes(assets=index_assets)
        )
        ingest_records(db, records)
        symbols = [asset.symbol for asset in crypto_assets + currency_assets + index_assets]
        run_transformation_pipeline(db, symbols)
        run_aggregation_pipeline(db, symbols)
        logger.info("Crypto/currency pipeline completed")
    except Exception as exc:
        logger.error("Crypto/currency pipeline failed: %s", exc)
    finally:
        db.close()


def build_scheduler() -> BackgroundScheduler:
    """Create and configure the scheduler."""
    scheduler = BackgroundScheduler()

    # Stock / ETF prices – every weekday at market open (10:00 BRT = 13:00 UTC)
    # and at close (17:00 BRT = 20:00 UTC)
    for hour in (13, 20):
        scheduler.add_job(
            _run_stocks_pipeline,
            CronTrigger(day_of_week="mon-fri", hour=hour, minute=0, timezone="UTC"),
            id=f"stocks_{hour}",
            name=f"Stocks/ETF ingestion at {hour}:00 UTC",
            replace_existing=True,
        )

    # Crypto, currencies & macro indexes – every hour at :05
    scheduler.add_job(
        _run_crypto_currency_pipeline,
        CronTrigger(minute=5, timezone="UTC"),
        id="hourly_crypto_currency",
        name="Hourly crypto/currency ingestion",
        replace_existing=True,
    )

    return scheduler


def start_scheduler() -> BackgroundScheduler | None:
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled by configuration")
        return None
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler

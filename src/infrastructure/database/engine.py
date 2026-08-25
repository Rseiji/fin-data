from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from src.config.settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    Base.metadata.create_all(bind=engine)
    _migrate_tracked_assets()
    from src.infrastructure.database import repositories

    db = SessionLocal()
    try:
        repositories.ensure_default_tracked_assets(db)
    finally:
        db.close()


def _migrate_tracked_assets():
    columns = {column["name"] for column in inspect(engine).get_columns("tracked_assets")}
    with engine.begin() as connection:
        if "provider_symbol" not in columns:
            connection.execute(
                text("ALTER TABLE tracked_assets ADD COLUMN provider_symbol VARCHAR(128) NOT NULL DEFAULT ''")
            )
        if "provider_config" not in columns:
            connection.execute(
                text("ALTER TABLE tracked_assets ADD COLUMN provider_config JSON NOT NULL DEFAULT '{}'")
            )

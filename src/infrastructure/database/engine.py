from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from src.config.settings import settings

DATABASE_SCHEMA = settings.database_schema
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    metadata = MetaData(schema=DATABASE_SCHEMA)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    _ensure_database_schema()
    Base.metadata.create_all(bind=engine)
    from src.infrastructure.database import repositories

    db = SessionLocal()
    try:
        repositories.ensure_default_tracked_assets(db)
    finally:
        db.close()


def _ensure_database_schema():
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DATABASE_SCHEMA}"'))

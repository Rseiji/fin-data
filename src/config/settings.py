from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg2://localhost:5432/findata"
    database_schema: str = "fin_data"
    log_level: str = "INFO"
    scheduler_enabled: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    ingestion_lookback_days: int = 6


settings = Settings()

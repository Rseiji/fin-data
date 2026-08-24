from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg2://localhost:5432/findata"
    log_level: str = "INFO"
    scheduler_enabled: bool = True


settings = Settings()

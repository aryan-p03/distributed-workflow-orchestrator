from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_env: str = Field(default="development", validation_alias="APP_ENV")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    celery_log_level: str = Field(default="INFO", validation_alias="CELERY_LOG_LEVEL")
    database_url: str = Field(
        default="postgresql://dwo_user:dwo_password@localhost:5432/dwo",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    schema_sync_on_startup: bool = Field(default=True, validation_alias="SCHEMA_SYNC_ON_STARTUP")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

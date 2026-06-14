from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    api_port: int = Field(default=8000, validation_alias="API_PORT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

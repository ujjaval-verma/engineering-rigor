from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "example_app"
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    news_collector_port: int = 8003
    redis_url: str = "redis://redis:6379/0"
    cryptopanic_api_key: str = ""
    newsapi_key: str = ""
    news_poll_interval_sec: int = 60
    log_level: str = "info"
    log_format: str = "json"


settings = Settings()

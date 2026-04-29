from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    ml_service_port: int = 8002
    redis_url: str = "redis://redis:6379/0"
    duckdb_path: str = "/data/duckdb/warehouse.duckdb"
    trading_pairs: str = "BTCUSDT,ETHUSDT,SOLUSDT"
    log_level: str = "info"
    log_format: str = "json"

    @property
    def pairs_list(self) -> list[str]:
        return [p.strip().upper() for p in self.trading_pairs.split(",") if p.strip()]


settings = Settings()

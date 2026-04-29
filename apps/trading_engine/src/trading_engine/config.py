"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(str, Enum):
    TESTNET = "testnet"
    PAPER = "paper"
    LIVE = "live"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    trading_mode: TradingMode = TradingMode.TESTNET
    i_understand_risk: Literal["yes", "no"] = "no"

    binance_api_key: str = Field(default="")
    binance_api_secret: str = Field(default="")
    binance_testnet: bool = True

    trading_pairs: str = "BTCUSDT,ETHUSDT,SOLUSDT"
    default_timeframe: str = "5m"

    live_capital_cap_usdt: float = 200.0

    redis_url: str = "redis://redis:6379/0"
    database_url: str = "sqlite:////data/sqlite/trading.db"

    trading_engine_port: int = 8001

    log_level: str = "info"
    log_format: str = "json"

    risk_config_path: str = "/config/risk.yml"

    @property
    def pairs_list(self) -> list[str]:
        return [p.strip().upper() for p in self.trading_pairs.split(",") if p.strip()]

    @property
    def is_live(self) -> bool:
        return self.trading_mode == TradingMode.LIVE


settings = Settings()

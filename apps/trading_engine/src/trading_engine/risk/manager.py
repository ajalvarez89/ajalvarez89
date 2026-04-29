"""Risk manager — validates trading signals before execution.

Phase 0: stub class with config loading.
Phase 2: full implementation of all rules from `config/risk.yml`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade_pct: float
    max_position_pct_equity: float
    max_open_positions: int
    stop_atr_multiplier: float
    tp_atr_multiplier: float
    mandatory_stop_loss_pct: float
    daily_max_drawdown_pct: float
    max_consecutive_losses: int
    max_orders_per_minute: int
    max_slippage_bps: int

    @classmethod
    def from_yaml(cls, path: str | Path) -> "RiskConfig":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str | None = None


class RiskManager:
    """Validates each prospective order against the risk policy.

    Phase 0: only initialization and config loading.
    """

    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def check_signal(self, signal: dict) -> RiskCheckResult:  # noqa: ARG002
        # Phase 2 will inspect:
        #   - kill switch state
        #   - current equity, # open positions
        #   - daily drawdown
        #   - consecutive loss streak
        #   - rate limits
        #   - mandatory stop_loss presence
        return RiskCheckResult(allowed=False, reason="risk_manager_not_implemented_phase_0")

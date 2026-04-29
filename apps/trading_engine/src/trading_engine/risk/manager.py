"""Risk manager — validates each signal before execution.

Implements the rules documented in docs/risk-management.md and parameterised in
config/risk.yml. The manager is a plain object; callers pass it whatever live
state it needs to decide (open positions, daily PnL, kill switch).
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from trading_engine.strategies.base import TradingSignal


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade_pct: float = 0.01
    max_position_pct_equity: float = 0.05
    max_open_positions: int = 3
    stop_atr_multiplier: float = 1.5
    tp_atr_multiplier: float = 3.0
    mandatory_stop_loss_pct: float = 0.02
    daily_max_drawdown_pct: float = 0.03
    max_consecutive_losses: int = 4
    max_orders_per_minute: int = 5
    max_slippage_bps: int = 50

    @classmethod
    def from_yaml(cls, path: str | Path) -> "RiskConfig":
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        # accept percentages as decimals (0.01) directly
        return cls(**{k: data[k] for k in data if k in cls.__dataclass_fields__})


@dataclass
class RiskState:
    equity: float
    open_positions: int = 0
    consecutive_losses: int = 0
    daily_pnl: float = 0.0
    daily_starting_equity: float = 0.0
    cooldown_until_ts: float = 0.0


@dataclass
class CheckResult:
    allowed: bool
    reason: str | None = None
    sized_quantity: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


class RiskManager:
    def __init__(self, config: RiskConfig, *, kill_switch=None) -> None:
        self.config = config
        self.kill_switch = kill_switch
        self._order_timestamps: deque[float] = deque(maxlen=self.config.max_orders_per_minute * 4)

    # -- Public API ----------------------------------------------------------

    def check_signal(self, signal: TradingSignal, state: RiskState) -> CheckResult:
        c = self.config

        if self.kill_switch is not None and self.kill_switch.is_engaged():
            return CheckResult(False, reason="kill_switch_engaged")

        now_ts = time.time()
        if state.cooldown_until_ts and now_ts < state.cooldown_until_ts:
            return CheckResult(False, reason="cooldown_active")

        if state.open_positions >= c.max_open_positions:
            return CheckResult(False, reason="max_open_positions_reached")

        if state.daily_starting_equity > 0:
            dd = (state.daily_starting_equity - state.equity) / state.daily_starting_equity
            if dd >= c.daily_max_drawdown_pct:
                return CheckResult(False, reason="daily_max_drawdown_breached")

        if state.consecutive_losses >= c.max_consecutive_losses:
            return CheckResult(False, reason="consecutive_loss_streak")

        # rate limit (rolling 60s window)
        cutoff = now_ts - 60.0
        self._order_timestamps = deque([t for t in self._order_timestamps if t >= cutoff], maxlen=self._order_timestamps.maxlen)
        if len(self._order_timestamps) >= c.max_orders_per_minute:
            return CheckResult(False, reason="rate_limit_exceeded")

        if signal.target_price is None or signal.stop_loss is None:
            return CheckResult(False, reason="missing_price_or_stop")

        # Sizing: risk_per_trade_pct of equity divided by stop distance.
        entry = signal.target_price
        stop = signal.stop_loss
        stop_distance = abs(entry - stop)
        if stop_distance <= 0:
            return CheckResult(False, reason="invalid_stop_distance")

        risk_amount = state.equity * c.risk_per_trade_pct
        qty = risk_amount / stop_distance

        # Cap by max_position_pct_equity
        max_notional = state.equity * c.max_position_pct_equity
        if qty * entry > max_notional:
            qty = max_notional / entry

        if qty <= 0:
            return CheckResult(False, reason="zero_quantity")

        return CheckResult(
            allowed=True,
            sized_quantity=qty,
            stop_loss=stop,
            take_profit=signal.take_profit,
        )

    def record_order(self) -> None:
        self._order_timestamps.append(time.time())

    def trigger_cooldown(self, state: RiskState, minutes: int = 60) -> None:
        state.cooldown_until_ts = time.time() + minutes * 60

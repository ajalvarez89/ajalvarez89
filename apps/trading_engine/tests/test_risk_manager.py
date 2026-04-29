"""Risk manager unit tests."""
from __future__ import annotations

from trading_engine.risk.kill_switch import KillSwitch
from trading_engine.risk.manager import RiskConfig, RiskManager, RiskState
from trading_engine.strategies.base import TradingSignal


def _signal(side: str = "buy", entry: float = 100.0, stop: float = 98.0, tp: float = 104.0) -> TradingSignal:
    return TradingSignal(
        symbol="BTCUSDT",
        side=side,
        confidence=0.6,
        horizon_minutes=60,
        target_price=entry,
        stop_loss=stop,
        take_profit=tp,
        strategy="test",
    )


def _state(equity: float = 10_000.0, **kwargs) -> RiskState:
    return RiskState(equity=equity, daily_starting_equity=equity, **kwargs)


def test_check_signal_sizes_to_risk_per_trade():
    m = RiskManager(RiskConfig())
    res = m.check_signal(_signal(entry=100, stop=98), _state())
    assert res.allowed is True
    # risk_amount = 10_000 * 0.01 = 100; stop distance = 2; qty = 50
    assert res.sized_quantity is not None
    assert abs(res.sized_quantity - 50.0) < 1e-6


def test_check_signal_caps_to_max_position_pct():
    m = RiskManager(RiskConfig(max_position_pct_equity=0.01))
    res = m.check_signal(_signal(entry=100, stop=99), _state())
    assert res.allowed
    # max_notional = 10_000 * 0.01 = 100 -> qty = 1
    assert res.sized_quantity is not None and abs(res.sized_quantity - 1.0) < 1e-6


def test_check_signal_blocked_by_kill_switch():
    ks = KillSwitch()
    ks.engage(reason="t")
    m = RiskManager(RiskConfig(), kill_switch=ks)
    res = m.check_signal(_signal(), _state())
    assert not res.allowed
    assert res.reason == "kill_switch_engaged"


def test_check_signal_blocked_by_max_open_positions():
    m = RiskManager(RiskConfig(max_open_positions=2))
    res = m.check_signal(_signal(), _state(open_positions=2))
    assert not res.allowed
    assert res.reason == "max_open_positions_reached"


def test_check_signal_blocked_by_daily_drawdown():
    m = RiskManager(RiskConfig(daily_max_drawdown_pct=0.03))
    res = m.check_signal(_signal(), _state(equity=9_500.0))  # -5%
    assert not res.allowed
    assert res.reason == "daily_max_drawdown_breached"


def test_check_signal_blocked_by_consecutive_losses():
    m = RiskManager(RiskConfig(max_consecutive_losses=3))
    res = m.check_signal(_signal(), _state(consecutive_losses=3))
    assert not res.allowed
    assert res.reason == "consecutive_loss_streak"


def test_invalid_stop_distance():
    m = RiskManager(RiskConfig())
    res = m.check_signal(_signal(entry=100, stop=100), _state())
    assert not res.allowed
    assert res.reason == "invalid_stop_distance"

import math

import pandas as pd

from ml_service.backtest.runner import StrategyParams, run_backtest
from ml_service.features.technical import compute_features


def _make_features(n: int = 800) -> pd.DataFrame:
    prices = [100.0 + math.sin(i / 8.0) * 5 + i * 0.04 for i in range(n)]
    df = pd.DataFrame(
        {
            "open_time_ms": list(range(n)),
            "open": prices,
            "high": [p * 1.002 for p in prices],
            "low": [p * 0.998 for p in prices],
            "close": prices,
            "volume": [1.0] * n,
        }
    )
    return compute_features(df)


def test_run_backtest_returns_finite_metrics():
    feats = _make_features()
    report = run_backtest(feats, symbol="BTCUSDT", interval="1m", params=StrategyParams())
    assert report.symbol == "BTCUSDT"
    m = report.metrics
    assert math.isfinite(m.total_return_pct)
    assert math.isfinite(m.max_drawdown_pct)
    assert m.drawdown_band in {"green", "amber", "red"}
    assert m.n_trades >= 0


def test_drawdown_band_thresholds():
    from ml_service.backtest.runner import _compute_metrics

    # construct an equity curve with 10% drawdown -> green
    eq_green = [100, 105, 110, 99, 110, 120]
    m = _compute_metrics(eq_green, [], starting_equity=100)
    assert m.drawdown_band == "green"

    # 25% drawdown -> amber
    eq_amber = [100, 110, 80, 90, 95]
    m = _compute_metrics(eq_amber, [], starting_equity=100)
    assert m.drawdown_band == "amber"

    # 50% drawdown -> red
    eq_red = [100, 120, 60, 70, 80]
    m = _compute_metrics(eq_red, [], starting_equity=100)
    assert m.drawdown_band == "red"

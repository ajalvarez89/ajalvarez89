import math

import pandas as pd

from ml_service.features.technical import FeatureConfig, compute_features


def _candles(n: int = 250) -> pd.DataFrame:
    prices = [100.0 + math.sin(i / 7.0) + i * 0.05 for i in range(n)]
    df = pd.DataFrame(
        {
            "open_time_ms": list(range(n)),
            "open": prices,
            "high": [p * 1.001 for p in prices],
            "low": [p * 0.999 for p in prices],
            "close": prices,
            "volume": [1.0] * n,
        }
    )
    return df


def test_compute_features_adds_all_columns():
    df = compute_features(_candles())
    expected = ["ema_fast", "ema_slow", "rsi", "macd", "macd_signal", "macd_hist", "atr", "bb_pct", "bb_width", "adx", "obv", "log_ret_1", "log_ret_5", "log_ret_15", "log_ret_60", "close_to_ema_fast", "close_to_ema_slow"]
    for col in expected:
        assert col in df.columns, f"missing {col}"


def test_features_have_finite_values_at_tail():
    df = compute_features(_candles())
    last = df.iloc[-1]
    for col in ["rsi", "macd", "atr", "ema_fast", "ema_slow"]:
        v = float(last[col])
        assert v == v  # not NaN

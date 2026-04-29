"""Technical-indicator feature engineering for ML.

Mirrors the indicators used in trading_engine/strategies/multi_signal.py so the
ML model "sees" the same world its eventual consumer will trade in.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pandas_ta as ta


@dataclass(frozen=True)
class FeatureConfig:
    ema_fast: int = 50
    ema_slow: int = 200
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14
    bbands_length: int = 20
    bbands_std: float = 2.0
    return_horizons: tuple[int, ...] = (1, 5, 15, 60)


def compute_features(df: pd.DataFrame, cfg: FeatureConfig | None = None) -> pd.DataFrame:
    """Add indicator columns + log returns to a DataFrame of OHLCV candles."""
    cfg = cfg or FeatureConfig()
    df = df.copy()

    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = df[col].astype(float)

    df["ema_fast"] = ta.ema(df["close"], length=cfg.ema_fast)
    df["ema_slow"] = ta.ema(df["close"], length=cfg.ema_slow)
    df["rsi"] = ta.rsi(df["close"], length=cfg.rsi_period)

    macd = ta.macd(df["close"], fast=cfg.macd_fast, slow=cfg.macd_slow, signal=cfg.macd_signal)
    df["macd"] = macd[f"MACD_{cfg.macd_fast}_{cfg.macd_slow}_{cfg.macd_signal}"]
    df["macd_signal"] = macd[f"MACDs_{cfg.macd_fast}_{cfg.macd_slow}_{cfg.macd_signal}"]
    df["macd_hist"] = macd[f"MACDh_{cfg.macd_fast}_{cfg.macd_slow}_{cfg.macd_signal}"]

    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=cfg.atr_period)

    bb = ta.bbands(df["close"], length=cfg.bbands_length, std=cfg.bbands_std)
    bb_lower = bb[f"BBL_{cfg.bbands_length}_{cfg.bbands_std}"]
    bb_upper = bb[f"BBU_{cfg.bbands_length}_{cfg.bbands_std}"]
    bb_mid = bb[f"BBM_{cfg.bbands_length}_{cfg.bbands_std}"]
    df["bb_pct"] = (df["close"] - bb_lower) / (bb_upper - bb_lower).replace(0, pd.NA)
    df["bb_width"] = (bb_upper - bb_lower) / bb_mid.replace(0, pd.NA)

    df["adx"] = ta.adx(df["high"], df["low"], df["close"], length=14)[f"ADX_14"]
    df["obv"] = ta.obv(df["close"], df["volume"])

    log_close = (df["close"] / df["close"].shift(1)).apply(lambda x: pd.NA if pd.isna(x) else _safe_log(x))
    df["log_ret_1"] = log_close
    for h in cfg.return_horizons:
        if h == 1:
            continue
        df[f"log_ret_{h}"] = (df["close"] / df["close"].shift(h)).apply(
            lambda x: pd.NA if pd.isna(x) else _safe_log(x)
        )

    df["close_to_ema_fast"] = df["close"] / df["ema_fast"] - 1
    df["close_to_ema_slow"] = df["close"] / df["ema_slow"] - 1

    return df


def _safe_log(x: float) -> float:
    import math
    if x is None or x <= 0:
        return float("nan")
    return math.log(x)

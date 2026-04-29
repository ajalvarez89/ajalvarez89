"""MultiSignal strategy: EMA + RSI + MACD + ATR confluence.

Implements the baseline strategy described in docs/architecture.md and the
plan. Uses pandas-ta for indicators. Stops/targets are sized in ATR multiples
so the risk-manager can convert them into position sizing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd
import pandas_ta as ta

from trading_engine.strategies.base import BaseStrategy, TradingSignal


@dataclass
class MultiSignalParams:
    ema_fast: int = 50
    ema_slow: int = 200
    rsi_period: int = 14
    rsi_lower_band: float = 35.0
    rsi_upper_band: float = 65.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14
    stop_atr_mult: float = 1.5
    tp_atr_mult: float = 3.0
    name: str = "multi_signal"
    timeframe: str = "5m"
    min_history: int = 220  # need EMA200 to be valid


@dataclass
class MultiSignalState:
    """Per-symbol state — tracks the last MACD diff to detect crossovers."""
    last_macd_hist_sign: int = 0
    last_signal_open_time_ms: int = 0


class MultiSignalStrategy(BaseStrategy):
    """Stateless evaluator over the last N closed candles for one symbol."""
    name = "multi_signal"

    def __init__(self, params: MultiSignalParams | None = None) -> None:
        self.params = params or MultiSignalParams()
        self._state: dict[str, MultiSignalState] = {}

    def evaluate(self, symbol: str, candles: Iterable[dict]) -> TradingSignal | None:
        df = self._df(candles)
        p = self.params

        if len(df) < p.min_history:
            return None

        df["ema_fast"] = ta.ema(df["close"], length=p.ema_fast)
        df["ema_slow"] = ta.ema(df["close"], length=p.ema_slow)
        df["rsi"] = ta.rsi(df["close"], length=p.rsi_period)
        macd = ta.macd(df["close"], fast=p.macd_fast, slow=p.macd_slow, signal=p.macd_signal)
        df["macd"] = macd[f"MACD_{p.macd_fast}_{p.macd_slow}_{p.macd_signal}"]
        df["macd_signal"] = macd[f"MACDs_{p.macd_fast}_{p.macd_slow}_{p.macd_signal}"]
        df["macd_hist"] = macd[f"MACDh_{p.macd_fast}_{p.macd_slow}_{p.macd_signal}"]
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=p.atr_period)

        # Use the last fully-closed candle for the decision.
        last = df.iloc[-1]
        prev = df.iloc[-2]

        if any(pd.isna(last[col]) for col in ("ema_fast", "ema_slow", "rsi", "macd", "macd_signal", "atr")):
            return None

        state = self._state.setdefault(symbol, MultiSignalState())
        prev_hist_sign = 1 if prev["macd_hist"] > 0 else (-1 if prev["macd_hist"] < 0 else 0)
        last_hist_sign = 1 if last["macd_hist"] > 0 else (-1 if last["macd_hist"] < 0 else 0)
        macd_cross_up = prev_hist_sign <= 0 and last_hist_sign > 0
        macd_cross_down = prev_hist_sign >= 0 and last_hist_sign < 0

        price = float(last["close"])
        ema_fast = float(last["ema_fast"])
        ema_slow = float(last["ema_slow"])
        rsi = float(last["rsi"])
        atr = float(last["atr"])

        long_trend = price > ema_fast > ema_slow
        short_trend = price < ema_fast < ema_slow
        rsi_ok = p.rsi_lower_band < rsi < p.rsi_upper_band

        signal: TradingSignal | None = None

        if long_trend and rsi_ok and macd_cross_up:
            signal = self._build_signal(symbol, "buy", price, atr)
        elif short_trend and rsi_ok and macd_cross_down:
            signal = self._build_signal(symbol, "sell", price, atr)

        # update state regardless to track histogram sign
        state.last_macd_hist_sign = last_hist_sign

        if signal is not None:
            open_time = int(last.get("open_time_ms") or 0)
            if open_time and state.last_signal_open_time_ms == open_time:
                return None  # already emitted on this candle
            state.last_signal_open_time_ms = open_time

        return signal

    def generate_signal(self, features: dict) -> TradingSignal | None:
        symbol = features.get("symbol")
        candles = features.get("candles") or []
        if not symbol or not candles:
            return None
        return self.evaluate(symbol, candles)

    def _build_signal(self, symbol: str, side: str, price: float, atr: float) -> TradingSignal:
        p = self.params
        if side == "buy":
            stop = price - p.stop_atr_mult * atr
            tp = price + p.tp_atr_mult * atr
        else:
            stop = price + p.stop_atr_mult * atr
            tp = price - p.tp_atr_mult * atr

        return TradingSignal(
            symbol=symbol,
            side=side,
            confidence=0.6,
            horizon_minutes=60,
            target_price=price,
            stop_loss=round(stop, 8),
            take_profit=round(tp, 8),
            strategy=self.name,
        )

    @staticmethod
    def _df(candles: Iterable[dict]) -> pd.DataFrame:
        df = pd.DataFrame(candles)
        for col in ("open", "high", "low", "close", "volume"):
            if col in df.columns:
                df[col] = df[col].astype(float)
        return df

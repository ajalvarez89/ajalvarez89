"""ML filter — augments a base strategy by querying the ML service.

Wraps a `MultiSignalStrategy` and only emits a signal if the ML service's
`direction_prob` agrees (>= 0.55 for buy, <= 0.45 for sell). If the ML service
has no champion or returns no probability, the wrapper falls back to the base
strategy's decision (graceful degradation).
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from trading_engine.strategies.base import BaseStrategy, TradingSignal
from trading_engine.strategies.multi_signal import MultiSignalStrategy

log = structlog.get_logger(__name__)


@dataclass
class MLFilterParams:
    ml_service_url: str = "http://ml_service:8002"
    long_threshold: float = 0.55
    short_threshold: float = 0.45
    timeout_seconds: float = 1.5


class MLConfirmedStrategy(BaseStrategy):
    name = "multi_signal_ml"

    def __init__(self, base: MultiSignalStrategy, params: MLFilterParams | None = None) -> None:
        self.base = base
        self.params = params or MLFilterParams()

    def evaluate(self, symbol: str, candles) -> TradingSignal | None:
        signal = self.base.evaluate(symbol, candles)
        if signal is None:
            return None

        prob = self._fetch_direction_prob(symbol)
        if prob is None:
            # No model trained yet — pass through.
            return signal

        if signal.side == "buy" and prob < self.params.long_threshold:
            log.info("ml_filter.rejected_long", symbol=symbol, prob=prob)
            return None
        if signal.side == "sell" and prob > self.params.short_threshold:
            log.info("ml_filter.rejected_short", symbol=symbol, prob=prob)
            return None

        signal.strategy = self.name
        signal.confidence = max(signal.confidence, prob if signal.side == "buy" else 1 - prob)
        return signal

    def generate_signal(self, features):
        symbol = features.get("symbol")
        candles = features.get("candles") or []
        if not symbol or not candles:
            return None
        return self.evaluate(symbol, candles)

    def _fetch_direction_prob(self, symbol: str) -> float | None:
        url = f"{self.params.ml_service_url}/inference/predict"
        try:
            r = httpx.post(
                url,
                json={"symbol": symbol, "interval": self.base.params.timeframe, "horizon_minutes": 60},
                timeout=self.params.timeout_seconds,
            )
            if r.status_code != 200:
                return None
            return r.json().get("direction_prob")
        except (httpx.HTTPError, ValueError):
            return None

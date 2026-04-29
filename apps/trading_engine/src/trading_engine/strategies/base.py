"""BaseStrategy interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TradingSignal:
    symbol: str
    side: str  # "buy" or "sell"
    confidence: float
    horizon_minutes: int
    target_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    strategy: str = ""


class BaseStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def generate_signal(self, features: dict) -> TradingSignal | None:
        """Return a TradingSignal or None (no-op)."""

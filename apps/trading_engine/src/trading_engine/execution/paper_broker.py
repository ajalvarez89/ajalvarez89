"""Paper broker: deterministic, in-memory simulation of fills.

Intended for testnet/paper modes. Models slippage, fees, and instant
market fills at the latest tick price. Persists results into the same
SQLite tables Phoenix renders so the dashboard works identically across
modes.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import structlog

from trading_engine.persistence import repos
from trading_engine.persistence.db import session_scope
from trading_engine.persistence.models import Position
from trading_engine.strategies.base import TradingSignal

log = structlog.get_logger(__name__)


FEE_RATE = 0.001  # 0.10% taker
SLIPPAGE_BPS = 5  # 5 bps = 0.05%


@dataclass
class FillResult:
    order_id: int
    trade_id: int
    position_id: int | None
    realized_pnl: float | None
    fill_price: float
    fee: float


class PaperBroker:
    """Single-instance broker. Operates against the shared SQLite DB.

    Convention:
      - "buy" opens a long position (or covers a short).
      - "sell" closes a long position (or opens a short — Phase 5).
    Phase 2 keeps Spot semantics: long-only, sell flattens the position.
    """

    def __init__(self, *, mode: Literal["testnet", "paper", "live"] = "paper") -> None:
        self.mode = mode

    async def submit(
        self,
        *,
        signal: TradingSignal,
        quantity: float,
        last_price: float,
    ) -> FillResult:
        side = signal.side
        external_id = f"paper-{uuid.uuid4().hex[:12]}"

        # Apply slippage symmetrically against you.
        slip = last_price * (SLIPPAGE_BPS / 10_000.0)
        fill_price = last_price + slip if side == "buy" else last_price - slip
        fee = fill_price * quantity * FEE_RATE

        async with session_scope() as s:
            order = await repos.insert_order(
                s,
                external_id=external_id,
                symbol=signal.symbol,
                side=side,
                type="market",
                status="filled",
                quantity=quantity,
                price=fill_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                strategy=signal.strategy,
                mode=self.mode,
                payload={"slippage_bps": SLIPPAGE_BPS, "fee_rate": FEE_RATE, "broker": "paper"},
            )

            position = await repos.get_open_position(s, signal.symbol, signal.strategy)

            realized_pnl: float | None = None
            position_id: int | None = None

            if side == "buy":
                if position is None:
                    position = await repos.insert_position(
                        s,
                        symbol=signal.symbol,
                        side="long",
                        quantity=quantity,
                        avg_entry_price=fill_price,
                        unrealized_pnl=0.0,
                        realized_pnl=0.0,
                        strategy=signal.strategy,
                        mode=self.mode,
                        opened_at=datetime.now(timezone.utc),
                    )
                else:
                    new_qty = position.quantity + quantity
                    position.avg_entry_price = (
                        position.avg_entry_price * position.quantity + fill_price * quantity
                    ) / new_qty
                    position.quantity = new_qty
                position_id = position.id
            else:  # sell
                if position is not None:
                    sell_qty = min(quantity, position.quantity)
                    realized_pnl = (fill_price - position.avg_entry_price) * sell_qty - fee
                    position.realized_pnl = (position.realized_pnl or 0.0) + realized_pnl
                    position.quantity -= sell_qty
                    if position.quantity <= 1e-12:
                        position.closed_at = datetime.now(timezone.utc)
                        position.quantity = 0.0
                    position_id = position.id

            trade = await repos.insert_trade(
                s,
                order_id=order.id,
                position_id=position_id,
                symbol=signal.symbol,
                side=side,
                quantity=quantity,
                price=fill_price,
                fee=fee,
                fee_asset=_quote_asset(signal.symbol),
                realized_pnl=realized_pnl,
                mode=self.mode,
                executed_at=datetime.now(timezone.utc),
            )

            await repos.insert_audit(
                s,
                actor=f"strategy:{signal.strategy or '?'}",
                action="paper_fill",
                payload={
                    "order_id": order.id,
                    "trade_id": trade.id,
                    "symbol": signal.symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": fill_price,
                    "realized_pnl": realized_pnl,
                },
            )

            return FillResult(
                order_id=order.id,
                trade_id=trade.id,
                position_id=position_id,
                realized_pnl=realized_pnl,
                fill_price=fill_price,
                fee=fee,
            )


def _quote_asset(symbol: str) -> str:
    for q in ("USDT", "BUSD", "USDC", "BTC", "ETH"):
        if symbol.endswith(q):
            return q
    return "USDT"

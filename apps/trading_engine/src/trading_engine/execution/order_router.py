"""Order router: applies risk-manager checks then dispatches to the broker."""
from __future__ import annotations

import structlog

from trading_engine.execution.paper_broker import FillResult, PaperBroker
from trading_engine.persistence import repos
from trading_engine.persistence.db import session_scope
from trading_engine.risk.manager import RiskManager, RiskState
from trading_engine.strategies.base import TradingSignal

log = structlog.get_logger(__name__)


class OrderRouter:
    def __init__(self, *, risk: RiskManager, paper_broker: PaperBroker, mode: str) -> None:
        self.risk = risk
        self.paper_broker = paper_broker
        self.mode = mode

    async def handle(self, signal: TradingSignal, *, state: RiskState, last_price: float) -> FillResult | None:
        # Approval gate — query the latest non-revoked, non-expired approval.
        async with session_scope() as s:
            approval = await repos.latest_active_approval(s)

        if approval is None:
            log.info(
                "order_rejected",
                reason="no_active_approval",
                strategy=signal.strategy,
                symbol=signal.symbol,
            )
            return None

        check = self.risk.check_signal(signal, state)
        if not check.allowed:
            log.info(
                "order_rejected",
                reason=check.reason,
                strategy=signal.strategy,
                symbol=signal.symbol,
            )
            async with session_scope() as s:
                await repos.insert_audit(
                    s,
                    actor=f"risk_manager",
                    action="reject_signal",
                    payload={"reason": check.reason, "symbol": signal.symbol, "side": signal.side, "strategy": signal.strategy},
                )
            return None

        # Phase 2: paper broker only. live_broker lands in Phase 7.
        if self.mode in ("testnet", "paper"):
            qty = check.sized_quantity or 0.0
            self.risk.record_order()
            fill = await self.paper_broker.submit(signal=signal, quantity=qty, last_price=last_price)
            log.info(
                "order_filled",
                strategy=signal.strategy,
                symbol=signal.symbol,
                side=signal.side,
                qty=qty,
                price=fill.fill_price,
                realized_pnl=fill.realized_pnl,
            )
            return fill

        # live mode falls back to the same paper-broker until Phase 7 wires
        # the real live broker. It also requires I_UNDERSTAND_RISK=yes which is
        # enforced at startup.
        log.warning("live_mode_not_yet_implemented_falling_back_to_paper")
        return await self.paper_broker.submit(signal=signal, quantity=check.sized_quantity or 0.0, last_price=last_price)

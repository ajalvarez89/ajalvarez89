"""Live broker — submits real orders to Binance Spot.

Phase 7 ships this code but does NOT enable it by default. Activation
requires:

  1. TRADING_MODE=live in .env
  2. I_UNDERSTAND_RISK=yes in .env
  3. `bash scripts/enable_live.sh` interactive confirmation
  4. `make up-live` (docker-compose.prod.yml override)
  5. An active 24h approval (`make approve`)
  6. The risk manager passing all checks (kill switch off, drawdown OK, etc.)
  7. The notional value of the order is below LIVE_CAPITAL_CAP_USDT.

The order router still calls PaperBroker by default; this class is wired
through the same OrderRouter only when `mode == "live"` AND
`settings.is_live` is true.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from binance import AsyncClient

from trading_engine.config import settings
from trading_engine.execution.paper_broker import FillResult
from trading_engine.persistence import repos
from trading_engine.persistence.db import session_scope
from trading_engine.strategies.base import TradingSignal

log = structlog.get_logger(__name__)


class LiveBroker:
    """Real order submission to Binance Spot. Read this carefully before use."""

    MAX_ORDER_USDT = settings.live_capital_cap_usdt

    def __init__(self, client: AsyncClient | None = None) -> None:
        self._client = client

    async def _ensure_client(self) -> AsyncClient:
        if self._client is None:
            if not settings.binance_api_key or settings.binance_api_key == "replace_me":
                raise RuntimeError("Live broker requires real BINANCE_API_KEY/SECRET.")
            self._client = await AsyncClient.create(
                api_key=settings.binance_api_key,
                api_secret=settings.binance_api_secret,
                testnet=settings.binance_testnet,  # respect mode
            )
        return self._client

    async def submit(
        self,
        *,
        signal: TradingSignal,
        quantity: float,
        last_price: float,
    ) -> FillResult:
        if not settings.is_live:
            raise RuntimeError("LiveBroker.submit called outside live mode")
        if settings.i_understand_risk != "yes":
            raise RuntimeError("LiveBroker.submit requires I_UNDERSTAND_RISK=yes")

        # Hard cap on notional
        notional = abs(quantity * last_price)
        if notional > self.MAX_ORDER_USDT:
            raise RuntimeError(f"Order notional {notional:.2f} > cap {self.MAX_ORDER_USDT:.2f}")

        client = await self._ensure_client()
        external_id = f"live-{uuid.uuid4().hex[:10]}"

        side = "BUY" if signal.side == "buy" else "SELL"
        # Round qty to step size if available — defer to Binance and let it 400 if invalid.
        params = {
            "symbol": signal.symbol,
            "side": side,
            "type": "MARKET",
            "quantity": _round_qty(signal.symbol, quantity),
            "newClientOrderId": external_id,
        }

        try:
            resp = await client.create_order(**params)
        except Exception as e:  # noqa: BLE001
            log.error("live_order_failed", error=str(e), symbol=signal.symbol, side=side)
            async with session_scope() as s:
                await repos.insert_audit(
                    s,
                    actor=f"strategy:{signal.strategy or '?'}",
                    action="live_order_failed",
                    payload={"error": str(e), "params": params},
                )
            raise

        fills = resp.get("fills", []) or []
        avg_price = float(resp.get("price") or last_price)
        executed_qty = float(resp.get("executedQty") or quantity)
        if fills:
            total_qty = sum(float(f["qty"]) for f in fills)
            avg_price = sum(float(f["qty"]) * float(f["price"]) for f in fills) / max(total_qty, 1e-12)

        fee = sum(float(f.get("commission", 0)) for f in fills)
        fee_asset = fills[0].get("commissionAsset") if fills else None

        async with session_scope() as s:
            order = await repos.insert_order(
                s,
                external_id=external_id,
                symbol=signal.symbol,
                side=signal.side,
                type="market",
                status="filled",
                quantity=executed_qty,
                price=avg_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                strategy=signal.strategy,
                mode="live",
                payload={"binance_order_id": resp.get("orderId"), "fills": fills},
            )

            position = await repos.get_open_position(s, signal.symbol, signal.strategy)
            position_id = None
            realized_pnl: float | None = None

            if signal.side == "buy":
                if position is None:
                    position = await repos.insert_position(
                        s,
                        symbol=signal.symbol,
                        side="long",
                        quantity=executed_qty,
                        avg_entry_price=avg_price,
                        unrealized_pnl=0.0,
                        realized_pnl=0.0,
                        strategy=signal.strategy,
                        mode="live",
                        opened_at=datetime.now(timezone.utc),
                    )
                else:
                    new_qty = position.quantity + executed_qty
                    position.avg_entry_price = (
                        position.avg_entry_price * position.quantity + avg_price * executed_qty
                    ) / new_qty
                    position.quantity = new_qty
                position_id = position.id
            else:
                if position is not None:
                    sell_qty = min(executed_qty, position.quantity)
                    realized_pnl = (avg_price - position.avg_entry_price) * sell_qty - fee
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
                side=signal.side,
                quantity=executed_qty,
                price=avg_price,
                fee=fee,
                fee_asset=fee_asset,
                realized_pnl=realized_pnl,
                mode="live",
                executed_at=datetime.now(timezone.utc),
            )

            await repos.insert_audit(
                s,
                actor=f"strategy:{signal.strategy or '?'}",
                action="live_fill",
                payload={
                    "order_id": order.id,
                    "trade_id": trade.id,
                    "binance_order_id": resp.get("orderId"),
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "qty": executed_qty,
                    "avg_price": avg_price,
                    "realized_pnl": realized_pnl,
                },
            )

            return FillResult(
                order_id=order.id,
                trade_id=trade.id,
                position_id=position_id,
                realized_pnl=realized_pnl,
                fill_price=avg_price,
                fee=fee,
            )


def _round_qty(symbol: str, qty: float) -> str:
    # Phase 7 minimal rounding: 6 decimals. Production would respect LOT_SIZE/stepSize from exchangeInfo.
    return f"{qty:.6f}"

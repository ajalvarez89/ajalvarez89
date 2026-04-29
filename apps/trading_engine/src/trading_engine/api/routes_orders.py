"""Order / position / trade query endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from trading_engine.persistence import repos
from trading_engine.persistence.db import session_scope

router = APIRouter(tags=["orders"])


def _to_dict(row, fields: list[str]) -> dict:
    return {f: _serialize(getattr(row, f, None)) for f in fields}


def _serialize(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


_ORDER_FIELDS = ["id", "external_id", "symbol", "side", "type", "status", "quantity", "price", "stop_loss", "take_profit", "strategy", "mode", "inserted_at"]
_POSITION_FIELDS = ["id", "symbol", "side", "quantity", "avg_entry_price", "unrealized_pnl", "realized_pnl", "strategy", "mode", "opened_at", "closed_at"]
_TRADE_FIELDS = ["id", "order_id", "position_id", "symbol", "side", "quantity", "price", "fee", "fee_asset", "realized_pnl", "mode", "executed_at"]


@router.get("/")
async def list_orders(limit: int = Query(50, ge=1, le=500)) -> dict:
    async with session_scope() as s:
        rows = await repos.list_recent_orders(s, limit=limit)
    return {"orders": [_to_dict(r, _ORDER_FIELDS) for r in rows]}


@router.get("/positions")
async def list_positions() -> dict:
    async with session_scope() as s:
        rows = await repos.list_open_positions(s)
    return {"positions": [_to_dict(r, _POSITION_FIELDS) for r in rows]}


@router.get("/trades")
async def list_trades(limit: int = Query(100, ge=1, le=1000)) -> dict:
    async with session_scope() as s:
        rows = await repos.list_recent_trades(s, limit=limit)
    return {"trades": [_to_dict(r, _TRADE_FIELDS) for r in rows]}


@router.get("/pnl")
async def pnl() -> dict:
    """Aggregate realized PnL by window: day, week, month, all."""
    now = datetime.now(timezone.utc)
    windows = {
        "day": now - timedelta(days=1),
        "week": now - timedelta(days=7),
        "month": now - timedelta(days=30),
        "year": now - timedelta(days=365),
    }
    async with session_scope() as s:
        trades = await repos.list_recent_trades(s, limit=10_000)

    out: dict[str, dict] = {}
    for window_name, since in windows.items():
        scoped = [t for t in trades if t.executed_at >= since.replace(tzinfo=None) or (t.executed_at.tzinfo and t.executed_at >= since)]
        # Robust to naive/aware datetimes from SQLite.
        scoped = [t for t in trades if _to_naive(t.executed_at) >= _to_naive(since)]
        realized = sum((t.realized_pnl or 0.0) for t in scoped)
        winners = sum(1 for t in scoped if (t.realized_pnl or 0) > 0)
        losers = sum(1 for t in scoped if (t.realized_pnl or 0) < 0)
        fees = sum((t.fee or 0.0) for t in scoped)
        win_rate = winners / (winners + losers) if (winners + losers) > 0 else 0.0
        out[window_name] = {
            "realized_pnl": round(realized, 4),
            "fees": round(fees, 4),
            "trades": len(scoped),
            "winners": winners,
            "losers": losers,
            "win_rate": round(win_rate, 4),
        }
    out["all_time"] = {
        "realized_pnl": round(sum((t.realized_pnl or 0.0) for t in trades), 4),
        "trades": len(trades),
    }
    return out


def _to_naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt

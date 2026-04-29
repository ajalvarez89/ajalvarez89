"""Repository helpers — narrow async functions used by the engine."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_engine.persistence.models import (
    Approval,
    AuditLog,
    Order,
    Position,
    Strategy,
    Trade,
)


# -- Audit ------------------------------------------------------------------


async def insert_audit(
    s: AsyncSession,
    *,
    actor: str,
    action: str,
    payload: dict | None = None,
    signature_hash: str | None = None,
) -> AuditLog:
    row = AuditLog(
        ts=datetime.now(timezone.utc),
        actor=actor,
        action=action,
        payload=payload or {},
        signature_hash=signature_hash,
    )
    s.add(row)
    await s.flush()
    return row


# -- Approvals --------------------------------------------------------------


async def latest_active_approval(s: AsyncSession) -> Approval | None:
    now = datetime.now(timezone.utc)
    stmt = (
        select(Approval)
        .where(Approval.action == "orders_approved")
        .where(Approval.revoked == False)  # noqa: E712
        .where(Approval.expires_at > now)
        .order_by(Approval.granted_at.desc())
        .limit(1)
    )
    return (await s.execute(stmt)).scalar_one_or_none()


async def insert_approval(s: AsyncSession, *, actor: str, ttl_hours: int = 24) -> Approval:
    now = datetime.now(timezone.utc)
    row = Approval(
        actor=actor,
        action="orders_approved",
        granted_at=now,
        expires_at=now.replace(microsecond=0) + _hours(ttl_hours),
    )
    s.add(row)
    await s.flush()
    return row


async def revoke_active_approvals(s: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    rows = (
        await s.execute(
            select(Approval).where(Approval.revoked == False).where(Approval.expires_at > now)  # noqa: E712
        )
    ).scalars().all()
    for r in rows:
        r.revoked = True
    await s.flush()
    return len(rows)


# -- Orders / Trades / Positions -------------------------------------------


async def insert_order(s: AsyncSession, **fields) -> Order:
    row = Order(**fields)
    s.add(row)
    await s.flush()
    return row


async def insert_trade(s: AsyncSession, **fields) -> Trade:
    row = Trade(**fields)
    s.add(row)
    await s.flush()
    return row


async def insert_position(s: AsyncSession, **fields) -> Position:
    row = Position(**fields)
    s.add(row)
    await s.flush()
    return row


async def get_open_position(s: AsyncSession, symbol: str, strategy: str | None = None) -> Position | None:
    stmt = (
        select(Position)
        .where(Position.symbol == symbol)
        .where(Position.closed_at.is_(None))
    )
    if strategy is not None:
        stmt = stmt.where(Position.strategy == strategy)
    return (await s.execute(stmt.order_by(Position.opened_at.desc()).limit(1))).scalar_one_or_none()


async def list_open_positions(s: AsyncSession) -> Sequence[Position]:
    stmt = select(Position).where(Position.closed_at.is_(None))
    return (await s.execute(stmt)).scalars().all()


async def list_recent_orders(s: AsyncSession, limit: int = 50) -> Sequence[Order]:
    stmt = select(Order).order_by(Order.inserted_at.desc()).limit(limit)
    return (await s.execute(stmt)).scalars().all()


async def list_recent_trades(s: AsyncSession, limit: int = 100) -> Sequence[Trade]:
    stmt = select(Trade).order_by(Trade.executed_at.desc()).limit(limit)
    return (await s.execute(stmt)).scalars().all()


# -- Strategies -------------------------------------------------------------


async def list_strategies(s: AsyncSession) -> Sequence[Strategy]:
    return (await s.execute(select(Strategy))).scalars().all()


async def get_strategy(s: AsyncSession, name: str) -> Strategy | None:
    return (await s.execute(select(Strategy).where(Strategy.name == name))).scalar_one_or_none()


async def upsert_strategy(s: AsyncSession, *, name: str, enabled: bool, symbols: list[str], timeframe: str, params: dict) -> Strategy:
    existing = await get_strategy(s, name)
    if existing:
        existing.enabled = enabled
        existing.symbols = symbols
        existing.timeframe = timeframe
        existing.params = params
        await s.flush()
        return existing
    row = Strategy(name=name, enabled=enabled, symbols=symbols, timeframe=timeframe, params=params)
    s.add(row)
    await s.flush()
    return row


# -- Helpers ----------------------------------------------------------------


def _hours(n: int):
    from datetime import timedelta
    return timedelta(hours=n)

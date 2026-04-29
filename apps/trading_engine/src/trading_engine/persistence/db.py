"""SQLAlchemy async engine and session helpers, sharing the SQLite file with Phoenix.

Phoenix owns the schema (Ecto migrations); we only read/write existing tables.
Foreign keys are pragmatically off in some Ecto migrations, so we don't enforce them here.
"""
from __future__ import annotations

import contextlib
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from trading_engine.config import settings


def _normalize_url(url: str) -> str:
    # Ecto/python-binance examples use sqlite:////data/sqlite/trading.db (4 slashes
    # for absolute paths). SQLAlchemy expects sqlite+aiosqlite://// with the same.
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


_engine = create_async_engine(_normalize_url(settings.database_url), future=True, echo=False)
SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


@contextlib.asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise

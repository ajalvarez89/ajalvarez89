"""Health and status endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request

from trading_engine.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "trading_engine",
        "version": "0.1.0",
        "mode": settings.trading_mode.value,
    }


@router.get("/health/binance")
async def binance_health(request: Request) -> dict:
    client = getattr(request.app.state, "binance", None)
    if client is None:
        return {"status": "not_initialized"}
    try:
        balances = await client.ping_and_balance()
        return {"status": "ok", "testnet": client.testnet, "balances": balances}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": str(e)}

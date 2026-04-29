"""Market data REST endpoints.

Public passthrough to Binance for historical klines. Used by Phoenix to
populate charts on first load before the WebSocket takes over for live updates.
"""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

log = structlog.get_logger(__name__)
router = APIRouter(tags=["market"])


_ALLOWED_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M",
}


@router.get("/klines")
async def klines(
    request: Request,
    symbol: Annotated[str, Query(min_length=5, max_length=20)],
    interval: Annotated[str, Query()] = "1m",
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    start_ms: Annotated[int | None, Query(ge=0)] = None,
    end_ms: Annotated[int | None, Query(ge=0)] = None,
) -> dict:
    if interval not in _ALLOWED_INTERVALS:
        raise HTTPException(status_code=400, detail=f"Unsupported interval: {interval}")

    client = getattr(request.app.state, "binance", None)
    if client is None:
        raise HTTPException(status_code=503, detail="binance client not initialized")

    try:
        rows = await client.get_klines(
            symbol,
            interval,
            limit=limit,
            start_ms=start_ms,
            end_ms=end_ms,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("klines_fetch_failed", error=str(e), symbol=symbol)
        raise HTTPException(status_code=502, detail=f"Binance error: {e}") from e

    return {"symbol": symbol.upper(), "interval": interval, "klines": rows}

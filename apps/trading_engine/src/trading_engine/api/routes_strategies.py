"""Strategy management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Body

from trading_engine.persistence import repos
from trading_engine.persistence.db import session_scope

router = APIRouter(tags=["strategies"])


@router.get("/")
async def list_strategies() -> dict:
    async with session_scope() as s:
        rows = await repos.list_strategies(s)
    return {
        "strategies": [
            {
                "id": r.id,
                "name": r.name,
                "enabled": r.enabled,
                "symbols": r.symbols or [],
                "timeframe": r.timeframe,
                "params": r.params or {},
            }
            for r in rows
        ]
    }


@router.post("/{name}/toggle")
async def toggle(name: str, enabled: bool = Body(..., embed=True)) -> dict:
    async with session_scope() as s:
        existing = await repos.get_strategy(s, name)
        if existing is None:
            return {"status": "not_found", "name": name}
        existing.enabled = enabled
        await repos.insert_audit(s, actor="user", action="toggle_strategy", payload={"name": name, "enabled": enabled})
    return {"status": "ok", "name": name, "enabled": enabled}

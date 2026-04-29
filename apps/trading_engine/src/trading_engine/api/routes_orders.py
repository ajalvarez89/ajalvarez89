"""Order endpoints — stubs in Phase 0, wired up in Phase 2."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["orders"])


@router.get("/")
async def list_orders() -> dict:
    return {"orders": [], "note": "Phase 0 stub. Real implementation in Phase 2."}

"""Admin endpoints: kill switch, resume, mode toggle."""
from __future__ import annotations

import structlog
from fastapi import APIRouter

from trading_engine.risk.kill_switch import KillSwitch

log = structlog.get_logger(__name__)
router = APIRouter(tags=["admin"])

_kill_switch = KillSwitch()


@router.post("/kill")
async def kill() -> dict:
    _kill_switch.engage(reason="manual_admin_call")
    log.warning("kill_switch.engaged", reason="manual_admin_call")
    return {"status": "ok", "engaged": True}


@router.post("/resume")
async def resume() -> dict:
    _kill_switch.disengage()
    log.info("kill_switch.disengaged")
    return {"status": "ok", "engaged": False}


@router.get("/status")
async def status() -> dict:
    return {"kill_switch": _kill_switch.status()}

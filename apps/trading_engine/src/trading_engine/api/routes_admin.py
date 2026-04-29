"""Admin endpoints: approval, kill switch, resume."""
from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter, Body, HTTPException, Request

from trading_engine.persistence import repos
from trading_engine.persistence.db import session_scope

log = structlog.get_logger(__name__)
router = APIRouter(tags=["admin"])


@router.post("/approve")
async def approve(
    request: Request,
    actor: str = Body("user", embed=True),
    ttl_hours: int = Body(24, embed=True),
) -> dict:
    if ttl_hours < 1 or ttl_hours > 72:
        raise HTTPException(status_code=400, detail="ttl_hours must be 1..72")
    async with session_scope() as s:
        approval = await repos.insert_approval(s, actor=actor, ttl_hours=ttl_hours)
        await repos.insert_audit(
            s,
            actor=actor,
            action="approve_orders",
            payload={"ttl_hours": ttl_hours, "expires_at": approval.expires_at.isoformat()},
        )
    return {
        "status": "ok",
        "approval_id": approval.id,
        "expires_at": approval.expires_at.isoformat(),
    }


@router.post("/kill")
async def kill(request: Request, reason: str = Body("manual", embed=True)) -> dict:
    request.app.state.kill_switch.engage(reason=reason)
    async with session_scope() as s:
        revoked = await repos.revoke_active_approvals(s)
        await repos.insert_audit(s, actor="user", action="kill_switch", payload={"reason": reason, "approvals_revoked": revoked})
    log.warning("kill_switch.engaged", reason=reason, approvals_revoked=revoked)
    return {"status": "ok", "engaged": True, "approvals_revoked": revoked}


@router.post("/resume")
async def resume(request: Request) -> dict:
    request.app.state.kill_switch.disengage()
    async with session_scope() as s:
        await repos.insert_audit(s, actor="user", action="resume", payload={})
    log.info("kill_switch.disengaged")
    return {"status": "ok", "engaged": False}


@router.get("/status")
async def status(request: Request) -> dict:
    async with session_scope() as s:
        approval = await repos.latest_active_approval(s)
    return {
        "kill_switch": request.app.state.kill_switch.status(),
        "approval": (
            None
            if approval is None
            else {
                "id": approval.id,
                "actor": approval.actor,
                "granted_at": approval.granted_at.isoformat(),
                "expires_at": approval.expires_at.isoformat(),
            }
        ),
    }

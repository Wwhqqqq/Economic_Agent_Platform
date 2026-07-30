"""Session execution context API — summon expert / manage skill binding."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.expert_catalog import get_expert
from app.core.session_context import (
    clear_session_expert,
    clear_session_skill,
    session_context_to_public,
    set_session_expert,
    set_session_skill,
)
from app.schemas.user_context import UserContext
from app.services.auth import AUTH_ENABLED, get_current_user
from app.skills.registry import skill_registry

router = APIRouter(prefix="/api/sessions", tags=["session-context"])


class SummonRequest(BaseModel):
    expert_id: str


class SkillBindRequest(BaseModel):
    skill: str
    skill_invocation: str | None = "explicit"


def _require_session_access(user: UserContext) -> None:
    if AUTH_ENABLED and user.user_id == 0:
        raise HTTPException(status_code=401, detail="未登录")


@router.get("/{session_id}/context")
async def get_session_context_api(
    session_id: str,
    user: UserContext = Depends(get_current_user),
):
    _require_session_access(user)
    return session_context_to_public(session_id)


@router.post("/{session_id}/summon")
async def summon_expert(
    session_id: str,
    req: SummonRequest,
    user: UserContext = Depends(get_current_user),
):
    _require_session_access(user)
    profile = get_expert(req.expert_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"专家 `{req.expert_id}` 不存在")

    runtime = profile.get("runtime") or {}
    set_session_expert(session_id, req.expert_id, engine=runtime.get("engine"))

    default_skill = runtime.get("default_skill")
    if default_skill and skill_registry.get(default_skill):
        set_session_skill(session_id, default_skill, "expert")

    return {"status": "summoned", **session_context_to_public(session_id)}


@router.delete("/{session_id}/summon")
async def unsummon_expert(
    session_id: str,
    user: UserContext = Depends(get_current_user),
):
    _require_session_access(user)
    clear_session_expert(session_id)
    ctx = session_context_to_public(session_id)
    if ctx.get("skill_invocation") == "expert":
        clear_session_skill(session_id)
        ctx = session_context_to_public(session_id)
    return {"status": "cleared", **ctx}


@router.post("/{session_id}/skill")
async def bind_skill(
    session_id: str,
    req: SkillBindRequest,
    user: UserContext = Depends(get_current_user),
):
    _require_session_access(user)
    if not skill_registry.get(req.skill):
        raise HTTPException(status_code=404, detail=f"技能 `{req.skill}` 不存在")
    set_session_skill(session_id, req.skill, req.skill_invocation or "explicit")
    return {"status": "bound", **session_context_to_public(session_id)}


@router.delete("/{session_id}/skill")
async def unbind_skill(
    session_id: str,
    user: UserContext = Depends(get_current_user),
):
    _require_session_access(user)
    from app.core.session_context import unbind_session_skill
    unbind_session_skill(session_id)
    return {"status": "cleared", **session_context_to_public(session_id)}

"""Per-session skill / expert state (WebSocket + REST scope)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

SESSION_DIR = os.path.join("data", "sessions")


@dataclass
class SessionContext:
    active_skill: Optional[str] = None
    active_expert_id: Optional[str] = None
    skill_invocation: Optional[str] = None  # slash | expert | explicit | None
    engine: Optional[str] = None
    context_strategy: dict = field(default_factory=dict)


_sessions: dict[str, SessionContext] = {}


def _session_path(session_id: str) -> str:
    safe = session_id.replace("/", "_").replace("\\", "_")
    return os.path.join(SESSION_DIR, f"{safe}.json")


def _load_persisted(session_id: str) -> SessionContext | None:
    path = _session_path(session_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SessionContext(
            active_skill=data.get("active_skill"),
            active_expert_id=data.get("active_expert_id"),
            skill_invocation=data.get("skill_invocation"),
            engine=data.get("engine"),
            context_strategy=data.get("context_strategy") or {},
        )
    except Exception:
        return None


def _persist(session_id: str, ctx: SessionContext) -> None:
    try:
        os.makedirs(SESSION_DIR, exist_ok=True)
        path = _session_path(session_id)
        payload = {
            "active_skill": ctx.active_skill,
            "active_expert_id": ctx.active_expert_id,
            "skill_invocation": ctx.skill_invocation,
            "engine": ctx.engine,
            "context_strategy": ctx.context_strategy,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception as exc:
        print(f"[SessionContext] persist skipped: {exc}")


def get_session_context(session_id: str) -> SessionContext:
    if session_id not in _sessions:
        _sessions[session_id] = _load_persisted(session_id) or SessionContext()
    return _sessions[session_id]


def set_session_skill(
    session_id: str,
    skill_name: Optional[str],
    invocation: Optional[str] = None,
) -> SessionContext:
    ctx = get_session_context(session_id)
    ctx.active_skill = skill_name
    if invocation:
        ctx.skill_invocation = invocation
    _persist(session_id, ctx)
    return ctx


def set_session_expert(session_id: str, expert_id: Optional[str], *, engine: str | None = None) -> SessionContext:
    ctx = get_session_context(session_id)
    ctx.active_expert_id = expert_id
    if engine:
        ctx.engine = engine
    _persist(session_id, ctx)
    return ctx


def unbind_session_skill(session_id: str) -> SessionContext:
    ctx = get_session_context(session_id)
    expert = None
    if ctx.active_expert_id:
        from app.core.expert_catalog import get_expert
        expert = get_expert(ctx.active_expert_id)
    default_skill = (expert.get("runtime") or {}).get("default_skill") if expert else None
    if default_skill:
        from app.skills.registry import skill_registry
        if skill_registry.get(default_skill):
            ctx.active_skill = default_skill
            ctx.skill_invocation = "expert"
            _persist(session_id, ctx)
            return ctx
    ctx.active_skill = None
    ctx.skill_invocation = None
    _persist(session_id, ctx)
    return ctx


def clear_session_skill(session_id: str) -> SessionContext:
    return unbind_session_skill(session_id)


def clear_session_expert(session_id: str) -> SessionContext:
    ctx = get_session_context(session_id)
    ctx.active_expert_id = None
    ctx.engine = None
    _persist(session_id, ctx)
    return ctx


def clear_session_context(session_id: str) -> None:
    _sessions.pop(session_id, None)
    path = _session_path(session_id)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def session_context_to_public(session_id: str) -> dict[str, Any]:
    ctx = get_session_context(session_id)
    from app.core.expert_catalog import get_expert
    from app.skills.registry import skill_registry

    expert = get_expert(ctx.active_expert_id) if ctx.active_expert_id else None
    skill = skill_registry.get(ctx.active_skill) if ctx.active_skill else None
    default_skill = None
    if expert:
        runtime = expert.get("runtime") or {}
        ds = runtime.get("default_skill")
        if ds:
            sk = skill_registry.get(ds)
            default_skill = {
                "name": ds,
                "display_name": sk.to_dict().get("display_name", ds) if sk else ds,
            }

    return {
        "session_id": session_id,
        "expert_id": ctx.active_expert_id,
        "expert_name": expert.get("name") if expert else None,
        "active_skill": ctx.active_skill,
        "active_skill_label": (
            skill.to_dict().get("display_name", ctx.active_skill) if skill else ctx.active_skill
        ),
        "skill_invocation": ctx.skill_invocation,
        "expert_default_skill": default_skill,
        "mode": _engine_to_mode(ctx.engine) or (expert.get("runtime", {}).get("mode") if expert else None),
    }


def _engine_to_mode(engine: Optional[str]) -> Optional[str]:
    if not engine:
        return None
    return {
        "plan_execute": "task_orchestration",
        "react": "reasoning_action",
        "team_protocol": "collaborative_decision",
    }.get(engine, engine)

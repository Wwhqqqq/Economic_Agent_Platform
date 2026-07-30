"""In-memory per-session skill / expert state (WebSocket chat scope)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SessionContext:
    active_skill: Optional[str] = None
    active_expert_id: Optional[str] = None
    skill_invocation: Optional[str] = None  # slash | expert | None


_sessions: dict[str, SessionContext] = {}


def get_session_context(session_id: str) -> SessionContext:
    if session_id not in _sessions:
        _sessions[session_id] = SessionContext()
    return _sessions[session_id]


def set_session_skill(
    session_id: str,
    skill_name: Optional[str],
    invocation: Optional[str] = None,
) -> None:
    ctx = get_session_context(session_id)
    ctx.active_skill = skill_name
    if invocation:
        ctx.skill_invocation = invocation


def set_session_expert(session_id: str, expert_id: Optional[str]) -> None:
    ctx = get_session_context(session_id)
    ctx.active_expert_id = expert_id


def clear_session_skill(session_id: str) -> None:
    ctx = get_session_context(session_id)
    ctx.active_skill = None
    ctx.skill_invocation = None


def clear_session_expert(session_id: str) -> None:
    ctx = get_session_context(session_id)
    ctx.active_expert_id = None


def clear_session_context(session_id: str) -> None:
    _sessions.pop(session_id, None)

"""Per-connection context for WebSocket sessions (skill activation, tool user scope)."""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConnectionContext:
    user_id: int = 0
    user_type: str = "regular"
    session_id: str = ""
    active_skill: Optional[str] = None


_connection_ctx: ContextVar[Optional[ConnectionContext]] = ContextVar(
    "connection_context", default=None
)


def set_connection_context(ctx: ConnectionContext) -> None:
    _connection_ctx.set(ctx)


def get_connection_context() -> Optional[ConnectionContext]:
    return _connection_ctx.get()


def get_active_skill_name() -> Optional[str]:
    ctx = get_connection_context()
    return ctx.active_skill if ctx else None


def get_tool_user_id() -> Optional[int]:
    ctx = get_connection_context()
    if ctx and ctx.user_id:
        return ctx.user_id
    return None

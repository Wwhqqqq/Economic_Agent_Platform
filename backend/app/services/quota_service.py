"""Quota checks and usage snapshots."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import ChatMessage, ChatSession
from app.db.models.system import SystemSetting
from app.services.knowledge_service import count_user_documents
from app.services.membership_gate import QuotaExceededError

DEFAULT_QUOTAS = {
    "regular": {
        "max_sessions": 20,
        "max_documents": 10,
        "max_file_mb": 5,
        "daily_messages": 100,
        "max_long_term_memories": 0,
    },
    "member": {
        "max_sessions": 500,
        "max_documents": 200,
        "max_file_mb": 20,
        "daily_messages": 2000,
        "max_long_term_memories": 500,
    },
}


async def _get_setting(db: AsyncSession, key: str, default: Any) -> Any:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = result.scalar_one_or_none()
    if not row:
        return default
    try:
        return json.loads(row.value_json)
    except json.JSONDecodeError:
        return default


async def get_quota_limits(db: AsyncSession, user_type: str) -> dict[str, int]:
    tier = "member" if user_type == "member" else "regular"
    defaults = DEFAULT_QUOTAS[tier]
    return {
        "max_sessions": int(
            await _get_setting(db, f"quota.{tier}.max_sessions", defaults["max_sessions"])
        ),
        "max_documents": int(
            await _get_setting(db, f"quota.{tier}.max_documents", defaults["max_documents"])
        ),
        "max_file_mb": int(
            await _get_setting(db, f"quota.{tier}.max_file_mb", defaults["max_file_mb"])
        ),
        "daily_messages": int(
            await _get_setting(db, f"quota.{tier}.daily_messages", defaults["daily_messages"])
        ),
        "max_long_term_memories": int(
            await _get_setting(
                db, f"quota.{tier}.max_long_term_memories", defaults["max_long_term_memories"]
            )
        ),
    }


async def count_user_sessions(db: AsyncSession, user_id: int) -> int:
    """Count non-deleted sessions (includes empty draft sessions)."""
    result = await db.execute(
        select(func.count())
        .select_from(ChatSession)
        .where(ChatSession.user_id == user_id, ChatSession.status != "deleted")
    )
    return int(result.scalar() or 0)


async def count_user_sessions_with_messages(db: AsyncSession, user_id: int) -> int:
    """Count sessions that have at least one persisted message (quota-relevant)."""
    result = await db.execute(
        select(func.count(func.distinct(ChatMessage.session_id)))
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatSession.status != "deleted",
        )
    )
    return int(result.scalar() or 0)


async def count_user_daily_messages(db: AsyncSession, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatSession.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= start_of_day,
        )
    )
    return int(result.scalar() or 0)


async def get_quota_snapshot(
    db: AsyncSession, user_id: int, user_type: str
) -> dict[str, Any]:
    limits = await get_quota_limits(db, user_type)
    sessions_used = await count_user_sessions_with_messages(db, user_id)
    documents_used = await count_user_documents(db, user_id)
    daily_used = await count_user_daily_messages(db, user_id)

    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta

    resets_at = tomorrow + timedelta(days=1)

    return {
        "sessions": {"used": sessions_used, "limit": limits["max_sessions"]},
        "documents": {"used": documents_used, "limit": limits["max_documents"]},
        "daily_messages": {
            "used": daily_used,
            "limit": limits["daily_messages"],
            "resets_at": resets_at.isoformat(),
        },
        "long_term_memories": {"used": 0, "limit": limits["max_long_term_memories"]},
        "max_file_mb": limits["max_file_mb"],
    }


async def check_quota(
    db: AsyncSession,
    action: str,
    user_id: int,
    user_type: str,
    *,
    file_size_bytes: Optional[int] = None,
) -> None:
    if user_id == 0:
        return

    limits = await get_quota_limits(db, user_type)

    if action == "create_session":
        used = await count_user_sessions_with_messages(db, user_id)
        limit = limits["max_sessions"]
        if used >= limit:
            raise QuotaExceededError(
                "max_sessions",
                f"有记录的对话已达上限（{used}/{limit}）。请删除不再需要的对话，或升级会员提升配额",
            )

    elif action == "upload_document":
        used = await count_user_documents(db, user_id)
        limit = limits["max_documents"]
        if used >= limit:
            raise QuotaExceededError(
                "max_documents",
                f"知识库文档数已达上限（{used}/{limit}），请升级会员",
            )
        if file_size_bytes is not None:
            max_bytes = limits["max_file_mb"] * 1024 * 1024
            if file_size_bytes > max_bytes:
                raise QuotaExceededError(
                    "max_file_mb",
                    f"单文件大小不能超过 {limits['max_file_mb']} MB",
                )

    elif action == "daily_message":
        used = await count_user_daily_messages(db, user_id)
        limit = limits["daily_messages"]
        if used >= limit:
            raise QuotaExceededError(
                "daily_messages",
                f"今日消息数已达上限（{used}/{limit}），请明天再试或升级会员",
            )


def quota_http_exception(exc: QuotaExceededError) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={
            "code": "QUOTA_EXCEEDED",
            "message": exc.message,
            "quota": exc.quota,
        },
    )

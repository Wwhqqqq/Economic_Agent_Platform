"""Chat session and message persistence."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import ChatMessage, ChatSession


class ChatSessionService:
    async def create_session(
        self,
        db: AsyncSession,
        user_id: int,
        title: str = "新对话",
    ) -> ChatSession:
        session = ChatSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            status="active",
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    async def get_owned_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
    ) -> Optional[ChatSession]:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.status != "deleted",
            )
        )
        return result.scalar_one_or_none()

    async def get_message_count(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
    ) -> int:
        session = await self.get_owned_session(db, session_id, user_id)
        if not session:
            return 0
        result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
        )
        return int(result.scalar_one() or 0)

    async def find_reusable_empty_session(
        self,
        db: AsyncSession,
        user_id: int,
        exclude_ids: Optional[list[str]] = None,
    ) -> Optional[ChatSession]:
        """Return the user's latest active session that has no messages."""
        msg_count = (
            select(ChatMessage.session_id, func.count(ChatMessage.id).label("cnt"))
            .group_by(ChatMessage.session_id)
            .subquery()
        )
        query = (
            select(ChatSession)
            .outerjoin(msg_count, ChatSession.id == msg_count.c.session_id)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.status != "deleted",
                func.coalesce(msg_count.c.cnt, 0) == 0,
            )
        )
        if exclude_ids:
            query = query.where(ChatSession.id.notin_(exclude_ids))
        result = await db.execute(
            query.order_by(ChatSession.updated_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, db: AsyncSession, user_id: int) -> list[dict]:
        msg_count = (
            select(func.count(ChatMessage.id))
            .where(ChatMessage.session_id == ChatSession.id)
            .correlate(ChatSession)
            .scalar_subquery()
        )
        result = await db.execute(
            select(ChatSession, msg_count.label("message_count"))
            .where(
                ChatSession.user_id == user_id,
                ChatSession.status != "deleted",
            )
            .order_by(ChatSession.updated_at.desc())
        )
        rows = result.all()
        return [
            {
                "session_id": session.id,
                "title": session.title,
                "message_count": int(count or 0),
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            }
            for session, count in rows
            if int(count or 0) > 0
        ]

    async def rename_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
        title: str,
    ) -> bool:
        session = await self.get_owned_session(db, session_id, user_id)
        if not session:
            return False
        session.title = title.strip() or "新对话"
        session.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return True

    async def soft_delete_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
    ) -> bool:
        session = await self.get_owned_session(db, session_id, user_id)
        if not session:
            return False
        session.status = "deleted"
        session.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        return True

    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
        role: str,
        content: str,
        tool_calls: Optional[list] = None,
        tokens_used: Optional[int] = None,
    ) -> None:
        session = await self.get_owned_session(db, session_id, user_id)
        if not session:
            raise ValueError("Session not found or access denied")

        if role == "user" and session.title == "新对话" and content.strip():
            session.title = content.strip()[:30] + ("..." if len(content.strip()) > 30 else "")

        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
            tokens_used=tokens_used,
        )
        db.add(msg)
        session.updated_at = datetime.now(timezone.utc)
        await db.flush()

    async def get_messages(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
    ) -> list[dict]:
        session = await self.get_owned_session(db, session_id, user_id)
        if not session:
            return []
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        messages = result.scalars().all()
        return [{"role": m.role, "content": m.content} for m in messages]

    async def get_langchain_messages(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
    ) -> list[BaseMessage]:
        session = await self.get_owned_session(db, session_id, user_id)
        if not session:
            return []
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        out: list[BaseMessage] = []
        for m in result.scalars().all():
            if m.role == "user":
                out.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                out.append(AIMessage(content=m.content))
            else:
                out.append(SystemMessage(content=m.content))
        return out

    async def get_history_summary(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
        max_messages: int = 10,
    ) -> str:
        session = await self.get_owned_session(db, session_id, user_id)
        if not session:
            return ""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(max_messages)
        )
        messages = list(reversed(result.scalars().all()))
        lines = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            content = msg.content[:200] if msg.content else ""
            lines.append(f"  {role}: {content}")
        return "\n".join(lines)

    async def delete_messages(self, db: AsyncSession, session_id: str, user_id: int) -> int:
        session = await self.get_owned_session(db, session_id, user_id)
        if not session:
            return 0
        result = await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        return result.rowcount or 0


chat_session_service = ChatSessionService()

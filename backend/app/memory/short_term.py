"""
短期记忆模块
管理当前会话的对话历史，支持 token 窗口管理
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.core.config import config


@dataclass
class SessionMeta:
    session_id: str
    title: str = "新对话"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_count: int = 0


class ShortTermMemory:
    """
    短期记忆 — 当前会话上下文

    使用滑动窗口策略管理对话历史：
    - 保留最近的 N 条消息
    - 自动裁剪使总 token 数不超过限制
    - 支持 RunnableConfig 注入，完美集成 LCEL
    """

    def __init__(self, max_tokens: int = None):
        self.max_tokens = max_tokens or config.memory.short_term_max_tokens
        self._messages: dict[str, list[BaseMessage]] = {}
        self._meta: dict[str, SessionMeta] = {}

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        """获取会话的所有消息"""
        return self._messages.get(session_id, [])

    def _touch_session(self, session_id: str, preview: str = "") -> None:
        if session_id not in self._meta:
            title = preview[:30] + ("..." if len(preview) > 30 else "") if preview else "新对话"
            self._meta[session_id] = SessionMeta(session_id=session_id, title=title)
        meta = self._meta[session_id]
        meta.updated_at = datetime.now(timezone.utc).isoformat()
        meta.message_count = len(self._messages.get(session_id, []))
        if meta.title == "新对话" and preview:
            meta.title = preview[:30] + ("..." if len(preview) > 30 else "")

    def add_message(
        self, session_id: str, message: BaseMessage
    ) -> None:
        """添加消息到会话历史"""
        if session_id not in self._messages:
            self._messages[session_id] = []
        self._messages[session_id].append(message)
        preview = message.content if isinstance(message.content, str) else str(message.content)
        if isinstance(message, HumanMessage):
            self._touch_session(session_id, preview)
        else:
            self._touch_session(session_id)
        self._trim(session_id)
        self._meta[session_id].message_count = len(self._messages[session_id])

    def add_user_message(self, session_id: str, content: str) -> None:
        self.add_message(session_id, HumanMessage(content=content))

    def add_ai_message(self, session_id: str, content: str) -> None:
        self.add_message(session_id, AIMessage(content=content))

    def add_system_message(self, session_id: str, content: str) -> None:
        """设置系统消息（每个会话只有一条，会覆盖之前的）"""
        msgs = self._messages.setdefault(session_id, [])
        # 移除旧的系统消息
        msgs[:] = [m for m in msgs if not isinstance(m, SystemMessage)]
        msgs.insert(0, SystemMessage(content=content))

    def _trim(self, session_id: str) -> None:
        """
        裁剪会话历史，确保总 token 数不超过限制
        保留 SystemMessage，裁剪人类/AI 消息对
        """
        messages = self._messages.get(session_id, [])
        estimated_tokens = self._count_tokens(messages)

        while estimated_tokens > self.max_tokens and len(messages) > 2:
            # 保留 system message，从前面移除对话消息
            for i, msg in enumerate(messages):
                if not isinstance(msg, SystemMessage):
                    messages.pop(i)
                    break
            estimated_tokens = self._count_tokens(messages)

    def _count_tokens(self, messages: list[BaseMessage]) -> int:
        """估算消息的 token 数量（粗略估算：中文1字≈1token，英文4char≈1token）"""
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            total += len(content)  # 粗略估算
        return total

    def clear(self, session_id: str) -> None:
        """清空会话历史"""
        self._messages.pop(session_id, None)
        self._meta.pop(session_id, None)

    def rename(self, session_id: str, title: str) -> bool:
        if session_id not in self._meta:
            return False
        self._meta[session_id].title = title.strip() or "新对话"
        self._meta[session_id].updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def list_sessions(self) -> list[dict]:
        sessions = []
        for sid, meta in self._meta.items():
            sessions.append({
                "session_id": sid,
                "title": meta.title,
                "message_count": len(self._messages.get(sid, [])),
                "created_at": meta.created_at,
                "updated_at": meta.updated_at,
            })
        sessions.sort(key=lambda s: s["updated_at"], reverse=True)
        return sessions

    def get_history_summary(self, session_id: str, max_messages: int = 10) -> str:
        """获取会话历史的摘要（用于注入到新的上下文）"""
        messages = self.get_messages(session_id)
        if not messages:
            return ""

        lines = []
        for msg in messages[-max_messages:]:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            content = msg.content[:200] if isinstance(msg.content, str) else str(msg.content)[:200]
            lines.append(f"  {role}: {content}")
        return "\n".join(lines)

    def to_runnable_config(self, session_id: str) -> RunnableConfig:
        """
        将短期记忆注入为 RunnableConfig

        这是 LCEL 集成的关键方法：
        chain.invoke(input, config=memory.to_runnable_config(session_id))
        """
        return RunnableConfig(
            configurable={
                "session_id": session_id,
                "messages": self.get_messages(session_id),
            }
        )

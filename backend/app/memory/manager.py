"""
记忆管理器 — 三层记忆 + 知识库 RAG 的统一编排
"""
import asyncio
import re
from typing import Optional

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda, RunnableConfig

from app.core.config import config as app_config
from app.core.connection_context import get_active_skill_name
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory
from app.memory.episodic import EpisodicMemory
from app.rag.entity_extractor import extract_entities
from app.rag.service import get_hybrid_retriever
from app.skills.registry import skill_registry


MEMORY_LOAD_TIMEOUT = 5.0


class MemoryManager:
    """三层记忆 + 知识库检索管理器"""

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()
        self._hybrid = get_hybrid_retriever()

    def _resolve_context_strategy(self, overrides: dict | None = None) -> dict:
        skill_name = get_active_skill_name()
        active_skill = skill_registry.get(skill_name) if skill_name else None
        strategy = active_skill.get_context_strategy() if active_skill else {
            "max_history": 10,
            "include_knowledge": True,
            "include_entities": True,
            "include_long_term": True,
        }
        if overrides:
            strategy = {**strategy, **overrides}
        return strategy

    async def load_context(
        self,
        session_id: str,
        user_input: str,
        system_prompt: str = None,
        *,
        context_strategy: dict | None = None,
    ) -> str:
        bundle = await self.load_context_bundle(
            session_id, user_input, system_prompt, context_strategy=context_strategy
        )
        return bundle["context"]

    async def load_context_bundle(
        self,
        session_id: str,
        user_input: str,
        system_prompt: str = None,
        *,
        user_id: int | None = None,
        user_type: str = "regular",
        context_strategy: dict | None = None,
    ) -> dict:
        """
        加载完整上下文，并返回结构化引用信息。
        """
        strategy = self._resolve_context_strategy(context_strategy)
        parts = []
        citations: list[dict] = []

        if system_prompt:
            parts.append(system_prompt)

        if strategy.get("include_knowledge", True) and len(user_input.strip()) > 2:
            try:
                docs = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self._hybrid.retrieve(
                            user_input,
                            app_config.memory.long_term_top_k,
                            "hybrid",
                            user_id=user_id,
                            user_type=user_type,
                        )
                    ),
                    timeout=MEMORY_LOAD_TIMEOUT,
                )
                if docs:
                    lines = ["## Retrieved Knowledge Base"]
                    for index, doc in enumerate(docs):
                        score = doc.metadata.get("score", doc.metadata.get("rrf_score", 0))
                        source = doc.metadata.get("source", "unknown")
                        doc_id = doc.metadata.get("doc_id", f"doc_{index}")
                        title = doc.metadata.get("entity_name") or doc_id
                        snippet = doc.page_content[:600]
                        lines.append(f"\n### [{source}] {title} (score: {float(score):.3f})")
                        lines.append(snippet)
                        citations.append({
                            "doc_id": doc_id,
                            "title": title,
                            "score": float(score),
                            "snippet": snippet[:200],
                            "source": source,
                        })
                    parts.append("\n".join(lines))
            except Exception as exc:
                print(f"[MemoryManager] Knowledge retrieval skipped: {exc}")

        if strategy.get("include_long_term", True):
            try:
                long_term_context = await asyncio.wait_for(
                    self.long_term.recall_formatted(user_input, user_id=user_id),
                    timeout=MEMORY_LOAD_TIMEOUT,
                )
                if long_term_context:
                    parts.append(long_term_context)
            except Exception as exc:
                print(f"[MemoryManager] Long-term recall skipped: {exc}")

        if strategy.get("include_entities", True):
            keywords = self._extract_keywords(user_input)
            if keywords and len(user_input.strip()) > 4:
                try:
                    graph_context = await asyncio.wait_for(
                        self.episodic.recall_graph_context(keywords[:5], user_id=user_id),
                        timeout=MEMORY_LOAD_TIMEOUT,
                    )
                    if graph_context:
                        parts.append(graph_context)
                except Exception as exc:
                    print(f"[MemoryManager] Episodic recall skipped: {exc}")

        max_history = strategy.get("max_history", 10)
        if user_id:
            from app.core.database import session_scope
            from app.services.chat_session_service import chat_session_service

            try:
                async with session_scope() as db:
                    chat_history = await chat_session_service.get_history_summary(
                        db, session_id, user_id, max_messages=max_history
                    )
            except Exception as exc:
                print(f"[MemoryManager] DB history skipped: {exc}")
                chat_history = ""
        else:
            chat_history = self.short_term.get_history_summary(
                session_id,
                max_messages=max_history,
            )
        if chat_history:
            parts.append(f"\n## Recent Conversation History\n{chat_history}")

        return {"context": "\n\n".join(parts), "citations": citations}

    def _extract_keywords(self, text: str) -> list[str]:
        keywords: list[str] = []
        cn_words = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
        keywords.extend(cn_words[:5])
        en_words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        keywords.extend(en_words[:3])
        for entity in extract_entities(text, limit=5):
            keywords.append(entity["name"])
        return list(dict.fromkeys(keywords))

    async def save_context(
        self,
        session_id: str,
        user_input: str,
        agent_output: str,
        entities: list[dict] = None,
        user_id: int | None = None,
    ) -> None:
        """保存对话到短期、长期、情景记忆。"""
        if user_id:
            from app.core.database import session_scope
            from app.services.chat_session_service import chat_session_service

            try:
                async with session_scope() as db:
                    await chat_session_service.add_message(
                        db, session_id, user_id, "user", user_input
                    )
                    await chat_session_service.add_message(
                        db, session_id, user_id, "assistant", agent_output
                    )
            except Exception as exc:
                print(f"[MemoryManager] DB save failed: {exc}")
        else:
            self.short_term.add_user_message(session_id, user_input)
            self.short_term.add_ai_message(session_id, agent_output)

        if entities is None:
            entities = extract_entities(f"{user_input}\n{agent_output}", limit=8)

        async def _persist_background():
            try:
                combined = f"User: {user_input}\nAssistant: {agent_output}"
                importance = 0.7 if len(agent_output) > 200 else 0.5
                await self.long_term.remember(
                    content=combined[:1200],
                    session_id=session_id,
                    user_id=user_id,
                    importance=importance,
                    metadata={"source": "conversation"},
                )
                await self.episodic.log_event(
                    session_id=session_id,
                    user_msg=user_input,
                    agent_msg=agent_output,
                    entities=entities,
                    user_id=user_id,
                )
            except Exception as exc:
                print(f"[MemoryManager] Background persist failed: {exc}")

        asyncio.create_task(_persist_background())

    def clear_session(self, session_id: str) -> None:
        """清除会话短期记忆。"""
        self.short_term.clear(session_id)

    async def clear_session_all(self, session_id: str, user_id: int | None = None) -> dict:
        """清除会话相关的短期、长期与情景记忆。"""
        if not user_id:
            self.short_term.clear(session_id)
        removed = await self.long_term.forget_session(session_id, user_id=user_id)
        episodic_removed = await self.episodic.clear_session(session_id, user_id=user_id)
        return {
            "session_id": session_id,
            "long_term_removed": removed,
            "episodic_removed": episodic_removed,
        }

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        return self.short_term.get_messages(session_id)

    async def as_runnable(self):
        async def _load_and_format(inputs: dict) -> dict:
            session_id = inputs.get("session_id", "default")
            user_input = inputs.get("input", "")
            context = await self.load_context(session_id, user_input)
            return {**inputs, "context": context}

        return RunnableLambda(_load_and_format)


memory_manager = MemoryManager()

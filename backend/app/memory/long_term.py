"""
长期记忆模块
基于 ChromaDB 向量检索的跨会话记忆

核心能力：
1. 将对话中的重要信息向量化存储
2. 新对话时通过语义检索召回相关历史信息
3. 支持记忆的增删改查
"""
import asyncio
import os
import uuid
from typing import Optional
from datetime import datetime

from app.core.config import config
from app.db.chroma import get_chroma_client
from app.rag.tenant_filter import build_user_filter

LONG_TERM_COLLECTION = "long_term_memory"
VECTOR_MEMORY_TIMEOUT = float(os.getenv("VECTOR_MEMORY_TIMEOUT", "5"))


class LongTermMemory:
    """
    长期记忆 — 基于向量检索的跨会话记忆

    本地 PersistentClient 模式下默认关闭向量记忆，避免首次对话
    触发 79MB embedding 模型下载导致长时间无响应。
    远程 ChromaDB（Docker）模式下自动启用。
    """

    def __init__(self):
        self._chroma = get_chroma_client()
        env_flag = os.getenv("ENABLE_VECTOR_MEMORY", "").lower()
        if env_flag == "true":
            self._enabled = True
        elif env_flag == "false":
            self._enabled = False
        else:
            self._enabled = self._chroma.is_remote

        if not self._enabled:
            print("[LongTermMemory] Vector memory disabled (local Chroma fallback). "
                  "Start Docker ChromaDB or set ENABLE_VECTOR_MEMORY=true to enable.")

    async def remember(
        self,
        content: str,
        session_id: str,
        metadata: dict = None,
        importance: float = 0.5,
        user_id: int | None = None,
    ) -> str:
        """存储一条长期记忆"""
        mem_id = str(uuid.uuid4())
        if not self._enabled:
            return mem_id

        meta = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "importance": importance,
            **(metadata or {}),
        }
        if user_id is not None:
            meta["user_id"] = int(user_id)
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    self._chroma.add_documents,
                    LONG_TERM_COLLECTION,
                    [mem_id],
                    [content],
                    [meta],
                    None,
                ),
                timeout=VECTOR_MEMORY_TIMEOUT,
            )
            print(f"[LongTermMemory] Stored: {mem_id[:8]}... (importance={importance})")
        except Exception as e:
            print(f"[LongTermMemory] Store skipped: {e}")
        return mem_id

    async def recall(
        self, query: str, top_k: int = None, min_importance: float = 0.0, user_id: int | None = None
    ) -> list[dict]:
        """检索相关长期记忆"""
        if not self._enabled:
            return []

        top_k = top_k or config.memory.long_term_top_k
        where = build_user_filter(user_id) if user_id is not None else None
        try:
            if where:
                count = await asyncio.wait_for(
                    asyncio.to_thread(self._chroma.count_where, LONG_TERM_COLLECTION, where),
                    timeout=VECTOR_MEMORY_TIMEOUT,
                )
            else:
                count = await asyncio.wait_for(
                    asyncio.to_thread(self._chroma.count, LONG_TERM_COLLECTION),
                    timeout=VECTOR_MEMORY_TIMEOUT,
                )
            if count == 0:
                return []

            results = await asyncio.wait_for(
                asyncio.to_thread(
                    self._chroma.query,
                    LONG_TERM_COLLECTION,
                    [query],
                    top_k,
                    where,
                ),
                timeout=VECTOR_MEMORY_TIMEOUT,
            )
        except Exception as e:
            print(f"[LongTermMemory] Recall skipped: {e}")
            self._enabled = False
            return []

        memories = []
        if results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                importance = meta.get("importance", 0)

                if importance >= min_importance:
                    memories.append({
                        "id": results["ids"][0][i],
                        "content": doc,
                        "metadata": meta,
                        "score": 1 - distance,
                    })

        if memories:
            print(f"[LongTermMemory] Recalled {len(memories)} memories for query")
        return memories

    async def recall_formatted(self, query: str, top_k: int = None, user_id: int | None = None) -> str:
        """检索并格式化为可注入上下文的文本"""
        memories = await self.recall(query, top_k, user_id=user_id)
        if not memories:
            return ""

        lines = ["## Relevant Past Knowledge"]
        for i, mem in enumerate(memories):
            lines.append(f"\n### Memory {i+1} (relevance: {mem['score']:.2f})")
            lines.append(mem["content"][:500])

        return "\n".join(lines)

    async def forget(self, memory_id: str) -> None:
        """删除指定记忆"""
        if not self._enabled:
            return
        try:
            await asyncio.to_thread(self._chroma.delete, LONG_TERM_COLLECTION, [memory_id])
        except Exception as e:
            print(f"[LongTermMemory] Forget failed: {e}")

    async def forget_session(self, session_id: str, user_id: int | None = None) -> int:
        """删除某个会话的所有记忆"""
        if not self._enabled:
            return 0
        try:
            where: dict = {"session_id": session_id}
            if user_id is not None:
                where = {"$and": [{"session_id": session_id}, {"user_id": int(user_id)}]}
            results = await asyncio.wait_for(
                asyncio.to_thread(
                    self._chroma.query,
                    LONG_TERM_COLLECTION,
                    [""],
                    100,
                    where,
                ),
                timeout=VECTOR_MEMORY_TIMEOUT,
            )
            if results.get("ids") and results["ids"][0]:
                ids_to_delete = results["ids"][0]
                await asyncio.to_thread(self._chroma.delete, LONG_TERM_COLLECTION, ids_to_delete)
                return len(ids_to_delete)
        except Exception as e:
            print(f"[LongTermMemory] Forget session failed: {e}")
        return 0

    def count(self) -> int:
        """记忆总数"""
        if not self._enabled:
            return 0
        try:
            return self._chroma.count(LONG_TERM_COLLECTION)
        except Exception:
            return 0

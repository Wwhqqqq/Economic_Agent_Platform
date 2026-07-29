"""
情景记忆模块
基于 Neo4j 知识图谱的会话事件与实体关系记忆

核心能力：
1. 记录用户-助手对话中的关键实体和关系
2. 构建用户知识图谱（兴趣、关注领域、历史查询主题）
3. 支持图谱查询注入到 Agent 上下文
"""
from typing import Optional
from datetime import datetime

from app.core.config import config
from app.db.neo4j import get_neo4j_client
from app.rag.entity_extractor import extract_entities


class EpisodicMemory:
    """
    情景记忆 — 基于知识图谱的会话记忆

    记录三个粒度的信息：
    1. Conversation: 会话节点（session_id, timestamp, topic）
    2. Entity: 讨论的实体（公司、人物、概念...）
    3. Relation: 实体间关系（投资、竞争、属于...）

    优势：
    - 支持结构化查询（"上次讨论XX公司时提到了什么？"）
    - 支持关系推理（"和XX相关的还有哪些公司？"）
    - 可视化展示（知识图谱）
    """

    def __init__(self):
        self._neo4j = get_neo4j_client()

    async def log_event(
        self,
        session_id: str,
        user_msg: str,
        agent_msg: str,
        entities: list[dict] = None,
        topic: str = None,
        user_id: int | None = None,
    ) -> None:
        """
        记录一次对话事件

        Args:
            session_id: 会话ID
            user_msg: 用户消息
            agent_msg: 助手回复
            entities: 提取的实体列表 [{"name": "Apple", "type": "Company"}, ...]
            topic: 对话主题
        """
        entities = entities or extract_entities(f"{user_msg}\n{agent_msg}", limit=8)

        self._neo4j.log_conversation(
            session_id=session_id,
            user_msg=user_msg,
            agent_msg=agent_msg,
            user_id=user_id,
            entities=[e["name"] for e in entities if e.get("name")],
        )

        print(f"[Episodic] Logged event for session {session_id[:8]}... "
              f"entities: {len(entities or [])}")

    async def recall_entities(
        self, query: str, entity_type: str = None
    ) -> list[dict]:
        """
        召回相关实体（通过知识图谱检索）
        """
        results = self._neo4j.search_entities(query, entity_type)
        return [
            {"name": r["e.name"], "type": r["e.type"], "properties": r.get("e", {})}
            for r in results
        ]

    async def recall_relations(
        self, entity_name: str, depth: int = 1
    ) -> list[dict]:
        """
        召回实体相关的关系
        """
        return self._neo4j.get_relations(entity_name, depth)

    async def recall_graph_context(self, entity_names: list[str], user_id: int | None = None) -> str:
        if not entity_names:
            return ""

        results = self._neo4j.graph_retrieve(entity_names, user_id=user_id)
        if not results:
            return ""

        lines = ["## Knowledge Graph Context"]
        for r in results:
            lines.append(
                f"- {r['source']} ({r.get('source_type', '')}) "
                f"--[{r['relation']}]--> "
                f"{r['target']} ({r.get('target_type', '')})"
            )

        return "\n".join(lines)

    async def get_session_topics(
        self, session_id: str, limit: int = 10
    ) -> list[str]:
        """
        获取会话的历史话题
        """
        results = self._neo4j._run(
            """
            MATCH (c:Conversation {session_id: $sid})-[:CONTAINS]->(m:Message)
            RETURN m.timestamp, m.user
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """,
            {"sid": session_id, "limit": limit},
        )
        return [r.get("m.user", "")[:100] for r in results]

    async def clear_session(self, session_id: str, user_id: int | None = None) -> int:
        return self._neo4j.clear_session(session_id, user_id=user_id)

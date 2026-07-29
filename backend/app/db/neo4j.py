"""
Neo4j 客户端封装
提供知识图谱的连接管理和 Cypher 查询接口

支持优雅降级：Neo4j 不可用时跳过多余操作
"""
from neo4j import GraphDatabase, Driver
from typing import Optional, Any
from dataclasses import dataclass

from app.core.config import config


@dataclass
class GraphEntity:
    """图谱实体"""
    name: str
    type: str
    properties: dict

    @classmethod
    def empty(cls):
        return cls(name="", type="", properties={})


@dataclass
class GraphRelation:
    """图谱关系"""
    source: str
    target: str
    relation: str
    properties: dict

    @classmethod
    def empty(cls):
        return cls(source="", target="", relation="", properties={})


class Neo4jClient:
    """Neo4j 客户端单例"""

    _instance: Optional["Neo4jClient"] = None

    def __init__(self):
        self._available: bool = False
        self._driver: Optional[Driver] = None
        try:
            self._driver = GraphDatabase.driver(
                config.neo4j.uri,
                auth=(config.neo4j.user, config.neo4j.password),
                connection_timeout=5,
            )
            self._driver.verify_connectivity()
            self._available = True
            self._init_schema()
            print(f"[Neo4j] Connected to {config.neo4j.uri}")
        except Exception as e:
            print(f"[Neo4j] Connection failed ({e}), knowledge graph features disabled")
            self._available = False

    @classmethod
    def get_instance(cls) -> "Neo4jClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def available(self) -> bool:
        return self._available

    def _init_schema(self) -> None:
        """初始化知识图谱 schema：创建索引"""
        if not self._available:
            return
        queries = [
            "CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.user_id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.type)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Conversation) ON (n.session_id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Conversation) ON (n.user_id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Document) ON (n.doc_id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Document) ON (n.user_id)",
        ]
        for q in queries:
            try:
                self._run(q)
            except Exception:
                pass

    def _run(self, query: str, params: dict = None) -> list[dict]:
        """执行 Cypher 查询"""
        if not self._available or not self._driver:
            return []
        try:
            with self._driver.session(database=config.neo4j.database) as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            print(f"[Neo4j] Query error: {e}")
            return []

    # ---- 实体操作 ----

    def upsert_entity(
        self,
        name: str,
        entity_type: str,
        user_id: int | None = None,
        properties: dict = None,
    ) -> None:
        if not self._available:
            return
        props = properties or {}
        uid = int(user_id or 0)
        self._run(
            """
            MERGE (e:Entity {user_id: $user_id, name: $name})
            SET e.type = $type
            SET e += $props
            SET e.updated_at = datetime()
            """,
            {"name": name, "type": entity_type, "user_id": uid, "props": props},
        )

    def get_entity(self, name: str, user_id: int | None = None) -> Optional[dict]:
        uid = int(user_id or 0)
        results = self._run(
            """
            MATCH (e:Entity {user_id: $user_id, name: $name})
            OPTIONAL MATCH (e)-[r]->(t:Entity)
            RETURN e.name AS name, e.type AS type, r, t
            LIMIT 30
            """,
            {"name": name, "user_id": uid},
        )
        return results if results else None

    def search_entities(
        self, keyword: str, user_id: int | None = None, entity_type: str = None
    ) -> list[dict]:
        uid = int(user_id or 0)
        type_filter = "AND e.type = $type" if entity_type else ""
        params: dict = {"keyword": f"(?i).*{keyword}.*", "user_id": uid}
        if entity_type:
            params["type"] = entity_type
        return self._run(
            f"""
            MATCH (e:Entity)
            WHERE e.user_id = $user_id AND e.name =~ $keyword {type_filter}
            RETURN e.name AS `e.name`, e.type AS `e.type`
            LIMIT 20
            """,
            params,
        )

    def count_entities(self, user_id: int | None = None) -> int:
        if user_id is None:
            results = self._run("MATCH (e:Entity) RETURN count(e) AS count")
        else:
            results = self._run(
                "MATCH (e:Entity {user_id: $user_id}) RETURN count(e) AS count",
                {"user_id": int(user_id)},
            )
        return results[0].get("count", 0) if results else 0

    # ---- 文档节点 ----

    def upsert_document(
        self,
        doc_id: str,
        title: str,
        snippet: str,
        user_id: int | None = None,
        visibility: str = "private",
        properties: dict = None,
    ) -> None:
        if not self._available:
            return
        props = {
            **(properties or {}),
            "user_id": int(user_id or 0),
            "visibility": visibility,
        }
        self._run(
            """
            MERGE (d:Document {doc_id: $doc_id})
            SET d.title = $title
            SET d.snippet = $snippet
            SET d.user_id = $user_id
            SET d.visibility = $visibility
            SET d += $props
            SET d.updated_at = datetime()
            """,
            {
                "doc_id": doc_id,
                "title": title,
                "snippet": snippet[:1000],
                "user_id": int(user_id or 0),
                "visibility": visibility,
                "props": props,
            },
        )

    def link_document_entity(self, doc_id: str, entity_name: str, user_id: int | None = None) -> None:
        if not self._available:
            return
        uid = int(user_id or 0)
        self.upsert_entity(entity_name, "Concept", user_id=uid)
        self._run(
            """
            MATCH (d:Document {doc_id: $doc_id, user_id: $user_id})
            MATCH (e:Entity {user_id: $user_id, name: $entity_name})
            MERGE (d)-[:MENTIONS]->(e)
            """,
            {"doc_id": doc_id, "entity_name": entity_name, "user_id": uid},
        )

    def search_documents(
        self, keyword: str, user_id: int | None = None, limit: int = 5, visibility: str = "private"
    ) -> list[dict]:
        uid = int(user_id or 0)
        return self._run(
            """
            MATCH (d:Document)
            WHERE d.user_id = $user_id
              AND d.visibility = $visibility
              AND (d.title =~ $keyword OR d.snippet =~ $keyword)
            RETURN d.doc_id AS doc_id, d.title AS title, d.snippet AS snippet
            LIMIT $limit
            """,
            {
                "keyword": f"(?i).*{keyword}.*",
                "user_id": uid,
                "visibility": visibility,
                "limit": limit,
            },
        )

    def count_documents(self, user_id: int | None = None, visibility: str = "private") -> int:
        if user_id is None:
            results = self._run("MATCH (d:Document) RETURN count(d) AS count")
        else:
            results = self._run(
                """
                MATCH (d:Document {user_id: $user_id, visibility: $visibility})
                RETURN count(d) AS count
                """,
                {"user_id": int(user_id), "visibility": visibility},
            )
        return results[0].get("count", 0) if results else 0

    # ---- 关系操作 ----

    def create_relation(
        self,
        source: str,
        target: str,
        relation: str,
        user_id: int | None = None,
        properties: dict = None,
    ) -> None:
        if not self._available:
            return
        uid = int(user_id or 0)
        props = properties or {}
        self._run(
            f"""
            MATCH (a:Entity {{user_id: $user_id, name: $source}})
            MATCH (b:Entity {{user_id: $user_id, name: $target}})
            MERGE (a)-[r:{relation}]->(b)
            SET r += $props
            SET r.created_at = datetime()
            """,
            {"source": source, "target": target, "user_id": uid, "props": props},
        )

    def get_relations(self, entity_name: str, depth: int = 1, user_id: int | None = None) -> list[dict]:
        uid = int(user_id or 0)
        return self._run(
            f"""
            MATCH (e:Entity {{user_id: $user_id, name: $name}})-[r*1..{depth}]-(related:Entity)
            WHERE related.user_id = $user_id
            RETURN e.name AS source, type(r[0]) AS relation, related.name AS target
            LIMIT 50
            """,
            {"name": entity_name, "user_id": uid},
        )

    # ---- 知识图谱增强检索 ----

    def graph_retrieve(
        self,
        entity_names: list[str],
        user_id: int | None = None,
        relation_types: list[str] = None,
    ) -> list[dict]:
        uid = int(user_id or 0)
        relation_filter = ""
        params: dict = {"names": entity_names, "user_id": uid}
        if relation_types:
            relation_filter = "AND type(r) IN $relations"
            params["relations"] = relation_types

        return self._run(
            f"""
            MATCH (e:Entity)-[r]->(t:Entity)
            WHERE e.user_id = $user_id AND t.user_id = $user_id
              AND e.name IN $names {relation_filter}
            RETURN e.name AS source, type(r) AS relation, t.name AS target,
                   e.type AS source_type, t.type AS target_type,
                   properties(r) AS rel_props
            LIMIT 30
            """,
            params,
        )

    # ---- 会话图谱 ----

    def log_conversation(
        self,
        session_id: str,
        user_msg: str,
        agent_msg: str,
        user_id: int | None = None,
        entities: list[str] = None,
    ) -> None:
        if not self._available:
            return
        uid = int(user_id or 0)
        entities = entities or []
        for entity_name in entities:
            self.upsert_entity(entity_name, "Concept", user_id=uid)
        self._run(
            """
            MERGE (c:Conversation {session_id: $session_id, user_id: $user_id})
            CREATE (m:Message {
                id: randomUUID(),
                user: $user_msg,
                agent: $agent_msg,
                user_id: $user_id,
                timestamp: datetime()
            })
            CREATE (c)-[:CONTAINS]->(m)
            """,
            {
                "session_id": session_id,
                "user_id": uid,
                "user_msg": user_msg,
                "agent_msg": agent_msg,
            },
        )
        if entities:
            self._run(
                """
                MATCH (m:Message)
                WHERE m.user = $user_msg AND m.agent = $agent_msg AND m.user_id = $user_id
                WITH m
                UNWIND $entities AS entity_name
                MATCH (e:Entity {user_id: $user_id, name: entity_name})
                MERGE (m)-[:MENTIONS]->(e)
                """,
                {
                    "user_msg": user_msg,
                    "agent_msg": agent_msg,
                    "user_id": uid,
                    "entities": entities,
                },
            )

    def delete_document(self, doc_id: str, user_id: int | None = None) -> None:
        if not self._available:
            return
        if user_id is None:
            self._run(
                """
                MATCH (d:Document {doc_id: $doc_id})
                DETACH DELETE d
                """,
                {"doc_id": doc_id},
            )
            return
        self._run(
            """
            MATCH (d:Document {doc_id: $doc_id, user_id: $user_id})
            DETACH DELETE d
            """,
            {"doc_id": doc_id, "user_id": int(user_id)},
        )

    def clear_session(self, session_id: str, user_id: int | None = None) -> int:
        if not self._available:
            return 0
        uid = int(user_id or 0)
        results = self._run(
            """
            MATCH (c:Conversation {session_id: $session_id, user_id: $user_id})-[:CONTAINS]->(m:Message)
            WITH c, collect(m) AS msgs
            FOREACH (x IN msgs | DETACH DELETE x)
            DETACH DELETE c
            RETURN size(msgs) AS removed
            """,
            {"session_id": session_id, "user_id": uid},
        )
        return results[0].get("removed", 0) if results else 0

    def close(self) -> None:
        if self._driver:
            self._driver.close()


def get_neo4j_client() -> Neo4jClient:
    return Neo4jClient.get_instance()

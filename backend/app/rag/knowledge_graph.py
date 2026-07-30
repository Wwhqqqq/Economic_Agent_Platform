"""
知识图谱检索器
基于 Neo4j 的结构化实体关系检索
"""
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.db.neo4j import get_neo4j_client
from app.rag.entity_extractor import extract_entities


class KnowledgeGraphRetriever:
    """知识图谱检索器 — 实体、关系、文档节点"""

    def __init__(self):
        self._neo4j = get_neo4j_client()

    @property
    def available(self) -> bool:
        return self._neo4j.available

    def add_entity(
        self, name: str, entity_type: str, user_id: int | None = None, properties: dict = None
    ) -> None:
        self._neo4j.upsert_entity(name, entity_type, user_id=user_id, properties=properties)

    def add_relation(
        self,
        source: str,
        target: str,
        relation: str,
        user_id: int | None = None,
        properties: dict = None,
    ) -> None:
        self._neo4j.create_relation(source, target, relation, user_id=user_id, properties=properties)

    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        user_id: int | None = None,
        visibility: str = "private",
        metadata: dict = None,
        entities: list[dict] | None = None,
    ) -> None:
        self._neo4j.upsert_document(
            doc_id=doc_id,
            title=title,
            snippet=content,
            user_id=user_id,
            visibility=visibility,
            properties=metadata or {},
        )
        entity_list = entities or extract_entities(content)
        for entity in entity_list:
            name = entity["name"]
            self._neo4j.upsert_entity(name, entity.get("type", "Concept"), user_id=user_id)
            self._neo4j.link_document_entity(doc_id, name, user_id=user_id)

    def link_document_entity(self, doc_id: str, entity_name: str, user_id: int | None = None) -> None:
        self._neo4j.link_document_entity(doc_id, entity_name, user_id=user_id)

    def upsert_chunk(
        self,
        chunk_id: str,
        doc_id: str,
        snippet: str,
        user_id: int | None = None,
        visibility: str = "private",
        section_path: str = "",
    ) -> None:
        self._neo4j.upsert_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            snippet=snippet,
            user_id=user_id,
            visibility=visibility,
            section_path=section_path,
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        depth: int = 1,
        *,
        user_id: int | None = None,
        user_type: str = "regular",
    ) -> list[Document]:
        _ = user_type  # Phase 3: member visibility branch
        documents: list[Document] = []
        keywords = [query] + [e["name"] for e in extract_entities(query, limit=5)]

        seen_keys: set[str] = set()
        rank = 0

        for keyword in keywords:
            if not keyword.strip():
                continue

            for doc in self._neo4j.search_documents(keyword, user_id=user_id, limit=top_k):
                key = doc.get("doc_id", doc.get("title", ""))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                score = max(0.35, 1.0 - rank * 0.08)
                documents.append(
                    Document(
                        page_content=(
                            f"Document: {doc.get('title', '')}\n"
                            f"{doc.get('snippet', '')[:800]}"
                        ),
                        metadata={
                            "doc_id": doc.get("doc_id"),
                            "source": "knowledge_graph",
                            "entity_name": doc.get("title", ""),
                            "score": score,
                        },
                    )
                )
                rank += 1

            entities = self._neo4j.search_entities(keyword, user_id=user_id)
            for entity in entities[:top_k]:
                entity_name = entity.get("e.name", "")
                if not entity_name or entity_name in seen_keys:
                    continue
                seen_keys.add(entity_name)
                entity_type = entity.get("e.type", "")
                relations = self._neo4j.get_relations(entity_name, depth, user_id=user_id)
                context = f"Entity: {entity_name} (Type: {entity_type})\n"
                if relations:
                    context += "Relations:\n"
                    for rel in relations[:10]:
                        context += f"  - {rel}\n"
                score = max(0.3, 0.85 - rank * 0.07)
                documents.append(
                    Document(
                        page_content=context,
                        metadata={
                            "entity_name": entity_name,
                            "entity_type": entity_type,
                            "source": "knowledge_graph",
                            "score": score,
                        },
                    )
                )
                rank += 1

            if len(documents) >= top_k:
                break

        return documents[:top_k]

    def retrieve_entity_context(self, entity_names: list[str], user_id: int | None = None) -> str:
        results = self._neo4j.graph_retrieve(entity_names, user_id=user_id)
        if not results:
            return ""

        lines = ["## Knowledge Graph Entities"]
        seen = set()
        for record in results:
            key = (record["source"], record["relation"], record["target"])
            if key not in seen:
                seen.add(key)
                lines.append(
                    f"- {record['source']} ({record.get('source_type', '')}) "
                    f"--[{record['relation']}]--> "
                    f"{record['target']} ({record.get('target_type', '')})"
                )
        return "\n".join(lines)

    def count_entities(self, user_id: int | None = None) -> int:
        return self._neo4j.count_entities(user_id)

    def count_documents(self, user_id: int | None = None, visibility: str = "private") -> int:
        return self._neo4j.count_documents(user_id, visibility=visibility)

    def delete_document(self, doc_id: str, user_id: int | None = None) -> None:
        self._neo4j.delete_document(doc_id, user_id=user_id)

    def upsert_metric_value(self, **kwargs) -> None:
        self._neo4j.upsert_metric_value(**kwargs)

    def as_retriever(self, top_k: int = 5, depth: int = 1):
        def _retrieve(query: str):
            return self.retrieve(query, top_k, depth)

        return RunnableLambda(_retrieve)

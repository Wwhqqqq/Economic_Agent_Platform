"""
混合检索器 — RRF (Reciprocal Rank Fusion) 融合策略

将向量检索（语义相似度）和知识图谱检索（实体关系/文档）的结果融合排序。
"""
from typing import Literal

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.rag.entity_extractor import build_document_title, extract_entities
from app.rag.knowledge_graph import KnowledgeGraphRetriever
from app.rag.vector_store import VectorStoreRetriever


class HybridRetriever:
    """混合检索器 — 向量 + 图谱 RRF 融合"""

    def __init__(self):
        self.vector_retriever = VectorStoreRetriever()
        self.graph_retriever = KnowledgeGraphRetriever()
        self._rrf_k: int = 60

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        mode: Literal["vector", "graph", "hybrid"] = "hybrid",
        rrf_k: int = None,
    ) -> list[Document]:
        if mode == "vector":
            return self.vector_retriever.retrieve(query, top_k)
        if mode == "graph":
            return self.graph_retriever.retrieve(query, top_k)
        if mode == "hybrid":
            return self._hybrid_retrieve(query, top_k, rrf_k)
        raise ValueError(f"Unknown mode: {mode}")

    def _hybrid_retrieve(
        self, query: str, top_k: int, rrf_k: int = None
    ) -> list[Document]:
        rrf_k = rrf_k or self._rrf_k
        vector_docs = self.vector_retriever.retrieve(query, top_k * 2)
        graph_docs = self.graph_retriever.retrieve(query, top_k * 2)
        fused = self._rrf_fusion(vector_docs, graph_docs, rrf_k)
        return fused[:top_k]

    def _rrf_fusion(
        self,
        docs_a: list[Document],
        docs_b: list[Document],
        k: int = 60,
    ) -> list[Document]:
        scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}

        for rank, doc in enumerate(docs_a):
            key = doc.metadata.get("doc_id") or doc.page_content[:50]
            scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
            doc_map[key] = doc

        for rank, doc in enumerate(docs_b):
            key = (
                doc.metadata.get("doc_id")
                or doc.metadata.get("entity_name")
                or doc.page_content[:50]
            )
            scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
            doc_map[key] = doc

        sorted_keys = sorted(scores.keys(), key=lambda item: scores[item], reverse=True)
        results = []
        for key in sorted_keys:
            doc = doc_map[key]
            doc.metadata["rrf_score"] = scores[key]
            doc.metadata["score"] = scores[key]
            doc.metadata["source"] = doc.metadata.get("source", "hybrid")
            results.append(doc)

        print(
            f"[HybridRetriever] Fused {len(docs_a)} vector + {len(docs_b)} graph "
            f"→ {len(results)} results"
        )
        return results

    def retrieve_formatted(
        self,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid",
    ) -> str:
        docs = self.retrieve(query, top_k, mode=mode)  # type: ignore[arg-type]
        if not docs:
            return ""

        lines = ["## Retrieved Knowledge Base"]
        for index, doc in enumerate(docs):
            score = doc.metadata.get(
                "score",
                doc.metadata.get("rrf_score", 0),
            )
            source = doc.metadata.get("source", "unknown")
            title = doc.metadata.get("entity_name") or doc.metadata.get("doc_id") or f"Doc {index + 1}"
            lines.append(f"\n### [{source}] {title} (score: {float(score):.3f})")
            lines.append(doc.page_content[:600])
        return "\n".join(lines)

    def as_runnable(self):
        def _retrieve(inputs: dict | str):
            if isinstance(inputs, str):
                query = inputs
            elif isinstance(inputs, dict):
                query = inputs.get("query", inputs.get("input", ""))
            else:
                query = str(inputs)

            docs = self.retrieve(query)
            return {
                "query": query,
                "context": self._docs_to_text(docs),
                "documents": docs,
            }

        return RunnableLambda(_retrieve)

    def _docs_to_text(self, docs: list[Document]) -> str:
        return "\n\n---\n\n".join(
            f"[{doc.metadata.get('source', 'doc')}]: {doc.page_content}"
            for doc in docs
        )

    def add_knowledge(
        self,
        content: str,
        doc_id: str,
        metadata: dict = None,
        entities: list[dict] = None,
    ) -> dict:
        """
        同时添加到向量库和知识图谱（自动抽取实体）。
        """
        meta = {"source": "knowledge_upload", **(metadata or {})}
        self.vector_retriever.add_document(content, doc_id, meta)

        extracted = entities or extract_entities(content)
        title = build_document_title(content, doc_id)
        self.graph_retriever.add_document(
            doc_id=doc_id,
            title=title,
            content=content,
            metadata=meta,
            entities=extracted,
        )

        for index, entity in enumerate(extracted):
            for other in extracted[index + 1 : index + 3]:
                try:
                    self.graph_retriever.add_relation(
                        entity["name"],
                        other["name"],
                        "RELATED_TO",
                        {"doc_id": doc_id},
                    )
                except Exception:
                    pass

        print(
            f"[HybridRetriever] Added knowledge: {doc_id} "
            f"(entities={len(extracted)})"
        )
        return {
            "doc_id": doc_id,
            "entities_extracted": len(extracted),
            "entities": extracted[:10],
        }

    def stats(self) -> dict:
        return {
            "vector_docs": self.vector_retriever.count(),
            "graph_entities": self.graph_retriever.count_entities(),
            "graph_documents": self.graph_retriever.count_documents(),
            "graph_available": self.graph_retriever.available,
        }

    def list_documents(self, limit: int = 100, offset: int = 0) -> list[dict]:
        return self.vector_retriever.list_documents(limit=limit, offset=offset)

    def delete_knowledge(self, doc_id: str) -> dict:
        self.vector_retriever.delete(doc_id)
        if self.graph_retriever.available:
            self.graph_retriever.delete_document(doc_id)
        return {"doc_id": doc_id, "status": "deleted"}

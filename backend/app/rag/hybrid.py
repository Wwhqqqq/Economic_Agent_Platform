from __future__ import annotations

import re
from typing import Literal

from langchain_core.documents import Document

from app.rag.chunk_store import get_chunk_store
from app.rag.entity_extractor import build_document_title, extract_entities
from app.rag.fact_store import get_fact_store
from app.rag.knowledge_graph import KnowledgeGraphRetriever
from app.rag.query_router import get_query_router
from app.rag.reranker import get_reranker
from app.rag.tenant_filter import knowledge_metadata
from app.rag.vector_store import VectorStoreRetriever


class HybridRetriever:
    """混合检索器 — Query Router + 向量 + 图谱 + Fact + Rerank"""

    def __init__(self):
        self.vector_retriever = VectorStoreRetriever()
        self.graph_retriever = KnowledgeGraphRetriever()
        self._chunk_store = get_chunk_store()
        self._query_router = get_query_router()
        self._reranker = get_reranker()
        self._fact_store = get_fact_store()
        self._rrf_k: int = 60

    def _hydrate_chunks(self, docs: list[Document]) -> list[Document]:
        chunk_ids = [
            doc.metadata.get("chunk_id")
            for doc in docs
            if doc.metadata.get("chunk_id")
        ]
        if not chunk_ids:
            return docs
        texts = self._chunk_store.get_texts_sync(chunk_ids)
        hydrated: list[Document] = []
        for doc in docs:
            chunk_id = doc.metadata.get("chunk_id")
            if chunk_id and chunk_id in texts:
                doc = Document(
                    page_content=texts[chunk_id],
                    metadata={**doc.metadata, "preview": doc.page_content[:200]},
                )
            hydrated.append(doc)
        return hydrated

    def _rrf_key(self, doc: Document) -> str:
        meta = doc.metadata
        if meta.get("fact_id"):
            return f"fact:{meta['fact_id']}"
        return (
            meta.get("chunk_id")
            or meta.get("doc_id")
            or meta.get("entity_name")
            or doc.page_content[:50]
        )

    def _facts_to_documents(self, facts: list[dict]) -> list[Document]:
        docs: list[Document] = []
        for i, fact in enumerate(facts):
            value = fact.get("value_text") or fact.get("value_num")
            text = (
                f"[FACT] {fact.get('metric_name', '')} "
                f"({fact.get('period', '')}) = {value} "
                f"{fact.get('unit', '')} · Page {fact.get('source_page', '')}"
            )
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": "fact_table",
                        "fact_id": fact.get("id"),
                        "doc_id": fact.get("doc_id"),
                        "metric_name": fact.get("metric_name"),
                        "page_no": fact.get("source_page"),
                        "content_type": "fact",
                        "score": 0.95 - i * 0.02,
                    },
                )
            )
        return docs

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        mode: Literal["vector", "graph", "hybrid"] = "hybrid",
        *,
        user_id: int | None = None,
        user_type: str = "regular",
        rrf_k: int | None = None,
        rerank: bool = True,
        content_types: list[str] | None = None,
    ) -> list[Document]:
        kwargs = {"user_id": user_id, "user_type": user_type}
        if mode == "vector":
            docs = self._hydrate_chunks(self.vector_retriever.retrieve(query, top_k, **kwargs))
            return self._reranker.rerank(query, docs, top_k=top_k) if rerank else docs[:top_k]
        if mode == "graph":
            return self.graph_retriever.retrieve(query, top_k, **kwargs)
        if mode == "hybrid":
            return self._hybrid_retrieve(
                query, top_k, rrf_k, rerank=rerank,
                content_types=content_types, **kwargs,
            )
        raise ValueError(f"Unknown mode: {mode}")

    def _hybrid_retrieve(
        self,
        query: str,
        top_k: int,
        rrf_k: int | None = None,
        *,
        user_id: int | None = None,
        user_type: str = "regular",
        rerank: bool = True,
        content_types: list[str] | None = None,
    ) -> list[Document]:
        rrf_k = rrf_k or self._rrf_k
        plan = self._query_router.analyze(query)
        if content_types:
            plan.content_types = content_types

        kwargs = {"user_id": user_id, "user_type": user_type}
        recall_k = max(top_k * 3, 15)

        vector_docs = self._hydrate_chunks(
            self.vector_retriever.retrieve(query, recall_k, **kwargs)
        )
        graph_docs = self.graph_retriever.retrieve(query, recall_k, **kwargs)

        fact_docs: list[Document] = []
        if plan.needs_fact and user_id:
            metric_hint = plan.entities[0] if plan.entities else None
            if not metric_hint:
                for kw in ["货币资金", "净利润", "营业收入", "资产总计", "ROE"]:
                    if kw in query:
                        metric_hint = kw
                        break
            facts = self._fact_store.query_facts(
                user_id=user_id,
                metric_name=metric_hint,
                period=plan.time_range,
                limit=recall_k,
            )
            fact_docs = self._facts_to_documents(facts)

        if plan.content_types:
            allowed = set(plan.content_types)
            vector_docs = [
                d for d in vector_docs
                if d.metadata.get("content_type", "paragraph") in allowed
                or not d.metadata.get("content_type")
            ]

        fused = self._rrf_fusion(
            vector_docs, graph_docs, rrf_k,
            extra_lists=[(fact_docs, plan.fact_weight)] if fact_docs else [],
        )
        if rerank:
            fused = self._reranker.rerank(query, fused, top_k=top_k)
        return fused[:top_k]

    def _rrf_fusion(
        self,
        docs_a: list[Document],
        docs_b: list[Document],
        k: int = 60,
        extra_lists: list[tuple[list[Document], float]] | None = None,
    ) -> list[Document]:
        scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}

        def _add(docs: list[Document], weight: float = 1.0) -> None:
            for rank, doc in enumerate(docs):
                key = self._rrf_key(doc)
                scores[key] = scores.get(key, 0) + weight * (1 / (k + rank + 1))
                if key not in doc_map:
                    doc_map[key] = doc

        _add(docs_a, 1.0)
        _add(docs_b, 1.0)
        for docs, weight in extra_lists or []:
            _add(docs, weight)

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
        *,
        user_id: int | None = None,
        user_type: str = "regular",
    ) -> str:
        docs = self.retrieve(
            query, top_k, mode=mode, user_id=user_id, user_type=user_type  # type: ignore[arg-type]
        )
        if not docs:
            return ""

        lines = ["## Retrieved Knowledge Base"]
        for index, doc in enumerate(docs):
            score = doc.metadata.get("score", doc.metadata.get("rrf_score", 0))
            source = doc.metadata.get("source", "unknown")
            title = (
                doc.metadata.get("section_path")
                or doc.metadata.get("entity_name")
                or doc.metadata.get("metric_name")
                or doc.metadata.get("doc_id")
                or f"Doc {index + 1}"
            )
            lines.append(f"\n### [{source}] {title} (score: {float(score):.3f})")
            lines.append(doc.page_content[:600])
        return "\n".join(lines)

    def as_runnable(self):
        def _retrieve(inputs: dict | str):
            if isinstance(inputs, str):
                query = inputs
                user_id = None
                user_type = "regular"
            elif isinstance(inputs, dict):
                query = inputs.get("query", inputs.get("input", ""))
                user_id = inputs.get("user_id")
                user_type = inputs.get("user_type", "regular")
            else:
                query = str(inputs)
                user_id = None
                user_type = "regular"

            docs = self.retrieve(query, user_id=user_id, user_type=user_type)
            return {
                "query": query,
                "context": self._docs_to_text(docs),
                "documents": docs,
            }

        from langchain_core.runnables import RunnableLambda
        return RunnableLambda(_retrieve)

    def _docs_to_text(self, docs: list[Document]) -> str:
        return "\n\n---\n\n".join(
            f"[{doc.metadata.get('source', 'doc')}]: {doc.page_content}"
            for doc in docs
        )

    def add_knowledge_chunks(
        self,
        chunks: list,
        *,
        doc_id: str,
        title: str,
        user_id: int,
        visibility: Literal["private", "member"] = "private",
        sample_text: str = "",
        extra_metadata: dict | None = None,
    ) -> dict:
        from app.rag.index_router import get_index_router

        router = get_index_router()
        router.index_document_header(
            doc_id=doc_id,
            title=title,
            user_id=user_id,
            visibility=visibility,
            sample_text=sample_text or title,
        )
        return router.index_chunks(
            chunks,
            doc_id=doc_id,
            user_id=user_id,
            visibility=visibility,
            extra_metadata=extra_metadata,
        )

    def add_knowledge(
        self,
        content: str,
        doc_id: str,
        *,
        user_id: int,
        visibility: Literal["private", "member"] = "private",
        metadata: dict = None,
        entities: list[dict] = None,
    ) -> dict:
        meta = knowledge_metadata(
            doc_id=doc_id,
            user_id=user_id,
            visibility=visibility,
            **(metadata or {}),
        )
        self.vector_retriever.add_document(
            content, doc_id, meta, user_id=user_id, visibility=visibility
        )

        extracted = entities or extract_entities(content)
        title = build_document_title(content, doc_id)
        self.graph_retriever.add_document(
            doc_id=doc_id,
            title=title,
            content=content,
            user_id=user_id,
            visibility=visibility,
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
                        user_id=user_id,
                        properties={"doc_id": doc_id},
                    )
                except Exception:
                    pass

        print(
            f"[HybridRetriever] Added knowledge: {doc_id} user={user_id} "
            f"(entities={len(extracted)})"
        )
        return {
            "doc_id": doc_id,
            "entities_extracted": len(extracted),
            "entities": extracted[:10],
        }

    def stats(self, user_id: int | None = None, user_type: str = "regular") -> dict:
        vector_docs = 0
        try:
            vector_docs = self.vector_retriever.count(user_id, user_type)
        except Exception as exc:
            print(f"[Hybrid] vector stats unavailable: {exc}")
        graph_entities = 0
        graph_documents = 0
        graph_available = self.graph_retriever.available
        if graph_available:
            try:
                graph_entities = self.graph_retriever.count_entities(user_id)
                graph_documents = self.graph_retriever.count_documents(user_id)
            except Exception as exc:
                print(f"[Hybrid] graph stats unavailable: {exc}")
        return {
            "vector_docs": vector_docs,
            "graph_entities": graph_entities,
            "graph_documents": graph_documents,
            "graph_available": graph_available,
        }

    def list_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        *,
        user_id: int | None = None,
        user_type: str = "regular",
    ) -> list[dict]:
        try:
            return self.vector_retriever.list_documents(
                limit=limit, offset=offset, user_id=user_id, user_type=user_type
            )
        except Exception as exc:
            print(f"[Hybrid] vector list_documents unavailable: {exc}")
            return []

    def delete_knowledge(self, doc_id: str, *, user_id: int | None = None) -> dict:
        from app.rag.fact_store import get_fact_store, get_table_store

        chunk_ids = self._chunk_store.list_chunk_ids_by_doc_sync(doc_id)
        self._chunk_store.delete_by_doc_sync(doc_id)
        get_table_store().delete_by_doc_sync(doc_id)
        get_fact_store().delete_by_doc_sync(doc_id)
        if chunk_ids:
            self.vector_retriever.delete_many(chunk_ids)
        self.vector_retriever.delete(doc_id)
        if self.graph_retriever.available:
            self.graph_retriever.delete_document(doc_id, user_id=user_id)
        return {"doc_id": doc_id, "status": "deleted", "chunks_removed": len(chunk_ids)}

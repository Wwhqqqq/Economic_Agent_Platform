from __future__ import annotations

from typing import Literal

from app.ingestion.chunker import ChunkRecord
from app.rag.entity_extractor import extract_entities
from app.rag.hybrid import HybridRetriever
from app.rag.knowledge_graph import KnowledgeGraphRetriever
from app.rag.fact_store import get_fact_store, get_table_store
from app.rag.tenant_filter import chunk_metadata, knowledge_metadata
from app.rag.vector_store import VectorStoreRetriever

PREVIEW_MAX_LEN = 200
SNIPPET_MAX_LEN = 200


class IndexRouter:
    """Route normalized chunks to vector + graph indexes."""

    def __init__(
        self,
        vector: VectorStoreRetriever | None = None,
        graph: KnowledgeGraphRetriever | None = None,
    ):
        self.vector = vector or VectorStoreRetriever()
        self.graph = graph or KnowledgeGraphRetriever()

    def index_document_header(
        self,
        *,
        doc_id: str,
        title: str,
        user_id: int,
        visibility: Literal["private", "member"] = "private",
        sample_text: str = "",
    ) -> None:
        """Create document-level graph node once per ingest."""
        snippet = (sample_text or title)[:1000]
        meta = knowledge_metadata(doc_id=doc_id, user_id=user_id, visibility=visibility)
        self.graph.add_document(
            doc_id=doc_id,
            title=title,
            content=snippet,
            user_id=user_id,
            visibility=visibility,
            metadata=meta,
            entities=extract_entities(sample_text or title),
        )

    def index_chunks(
        self,
        chunks: list[ChunkRecord],
        *,
        doc_id: str,
        user_id: int,
        visibility: Literal["private", "member"] = "private",
        extra_metadata: dict | None = None,
    ) -> dict:
        if not chunks:
            return {"chunks_indexed": 0, "entities_extracted": 0}

        previews: list[str] = []
        ids: list[str] = []
        metas: list[dict] = []
        all_entities: list[dict] = []

        for chunk in chunks:
            preview = chunk.text[:PREVIEW_MAX_LEN]
            meta = chunk_metadata(
                chunk_id=chunk.chunk_id,
                doc_id=doc_id,
                user_id=user_id,
                visibility=visibility,
                content_type=chunk.content_type,
                section_path=chunk.section_path,
                seq=chunk.seq,
                page_range=chunk.page_range,
                table_id=chunk.block_ids[0] if chunk.content_type.startswith("table") and chunk.block_ids else "",
                **(extra_metadata or {}),
            )
            previews.append(preview)
            ids.append(chunk.chunk_id)
            metas.append(meta)

            extracted = extract_entities(chunk.text)
            all_entities.extend(extracted)
            if self.graph.available:
                self.graph.upsert_chunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=doc_id,
                    snippet=chunk.text[:SNIPPET_MAX_LEN],
                    user_id=user_id,
                    visibility=visibility,
                    section_path=chunk.section_path,
                )
                for entity in extracted:
                    self.graph.link_document_entity(doc_id, entity["name"], user_id=user_id)

        self.vector.add_documents(previews, ids, metas)

        entity_names = {e["name"] for e in all_entities if e.get("name")}
        indexed_entities = list(entity_names)[:50]
        for i, name in enumerate(indexed_entities):
            for other in indexed_entities[i + 1 : i + 3]:
                try:
                    self.graph.add_relation(name, other, "RELATED_TO", user_id=user_id, properties={"doc_id": doc_id})
                except Exception:
                    pass

        return {
            "chunks_indexed": len(chunks),
            "entities_extracted": len(entity_names),
            "entities": [{"name": n, "type": "Concept"} for n in indexed_entities[:10]],
        }

    def index_tables_and_facts(
        self,
        *,
        doc_id: str,
        user_id: int,
        tables: list,
        facts: list,
        company: str | None = None,
    ) -> dict:
        table_store = get_table_store()
        fact_store = get_fact_store()
        table_count = table_store.insert_tables_sync(tables, doc_id=doc_id, user_id=user_id)
        fact_count = fact_store.insert_facts_sync(facts, doc_id=doc_id, user_id=user_id)

        if self.graph.available and facts:
            for fact in facts:
                try:
                    self.graph.upsert_metric_value(
                        user_id=user_id,
                        company=fact.company or company or "Unknown",
                        metric_name=fact.metric_name,
                        metric_code=fact.metric_code,
                        period=fact.period,
                        amount=fact.value_num,
                        raw_text=fact.value_text,
                        doc_id=doc_id,
                        table_id=fact.table_id,
                        source_page=fact.source_page,
                    )
                except Exception:
                    pass

        return {"tables_indexed": table_count, "facts_indexed": fact_count}

    def index_figure_facts(
        self,
        *,
        doc_id: str,
        user_id: int,
        facts: list,
        min_confidence: float = 0.7,
    ) -> dict:
        """Index high-confidence VLM figure facts."""
        if not facts:
            return {"figure_facts_indexed": 0}
        filtered = [f for f in facts if getattr(f, "confidence", 0) >= min_confidence]
        if not filtered:
            return {"figure_facts_indexed": 0}
        return self.index_tables_and_facts(
            doc_id=doc_id, user_id=user_id, tables=[], facts=filtered,
        )

    def delete_document_indexes(
        self,
        doc_id: str,
        chunk_ids: list[str],
        *,
        user_id: int | None = None,
    ) -> None:
        if chunk_ids:
            self.vector.delete_many(chunk_ids)
        self.vector.delete(doc_id)
        if self.graph.available:
            self.graph.delete_document(doc_id, user_id=user_id)


_index_router: IndexRouter | None = None


def get_index_router() -> IndexRouter:
    global _index_router
    if _index_router is None:
        _index_router = IndexRouter()
    return _index_router

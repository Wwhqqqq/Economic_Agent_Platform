from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.core.database import DATABASE_URL
from app.db.models.knowledge_chunk import KnowledgeChunk
from app.ingestion.chunker import ChunkRecord

SYNC_DATABASE_URL = DATABASE_URL.replace("+aiomysql", "+pymysql")

_sync_engine = None


def _engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)
    return _sync_engine


def _chunk_to_row(chunk: ChunkRecord, user_id: int) -> KnowledgeChunk:
    return KnowledgeChunk(
        id=chunk.chunk_id,
        doc_id=chunk.doc_id,
        user_id=user_id,
        seq=chunk.seq,
        content_type=chunk.content_type,
        text=chunk.text,
        token_count=chunk.token_count,
        section_path=chunk.section_path or None,
        page_range=chunk.page_range or None,
        block_ids=",".join(chunk.block_ids) if chunk.block_ids else None,
        content_hash=chunk.content_hash,
    )


class ChunkStore:
    """MySQL chunk authoritative store — sync reads for RAG hydration."""

    def insert_chunks_sync(self, chunks: list[ChunkRecord], user_id: int) -> int:
        if not chunks:
            return 0
        with Session(_engine()) as session:
            for chunk in chunks:
                session.merge(_chunk_to_row(chunk, user_id))
            session.commit()
        return len(chunks)

    def get_text_sync(self, chunk_id: str) -> Optional[str]:
        with Session(_engine()) as session:
            row = session.get(KnowledgeChunk, chunk_id)
            return row.text if row else None

    def get_texts_sync(self, chunk_ids: list[str]) -> dict[str, str]:
        if not chunk_ids:
            return {}
        with Session(_engine()) as session:
            rows = session.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.id.in_(chunk_ids))
            ).scalars().all()
            return {r.id: r.text for r in rows}

    def list_chunk_ids_by_doc_sync(self, doc_id: str) -> list[str]:
        with Session(_engine()) as session:
            rows = session.execute(
                select(KnowledgeChunk.id).where(KnowledgeChunk.doc_id == doc_id).order_by(KnowledgeChunk.seq)
            ).scalars().all()
            return list(rows)

    def delete_by_doc_sync(self, doc_id: str) -> int:
        with Session(_engine()) as session:
            result = session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc_id))
            session.commit()
            return result.rowcount or 0

    def count_by_doc_sync(self, doc_id: str) -> int:
        with Session(_engine()) as session:
            rows = session.execute(
                select(KnowledgeChunk.id).where(KnowledgeChunk.doc_id == doc_id)
            ).scalars().all()
            return len(rows)


_chunk_store: ChunkStore | None = None


def get_chunk_store() -> ChunkStore:
    global _chunk_store
    if _chunk_store is None:
        _chunk_store = ChunkStore()
    return _chunk_store

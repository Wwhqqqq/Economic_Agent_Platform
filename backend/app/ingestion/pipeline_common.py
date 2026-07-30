from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from app.ingestion.chunker import ChunkRecord
from app.ingestion.ndm import NormalizedDocument
from app.storage import doc_content_key, doc_ndm_key, get_storage


@dataclass
class IngestPipelineResult:
    doc_id: str
    title: str
    ndm: NormalizedDocument
    chunks: list[ChunkRecord]
    ndm_uri: str
    content_uri: str
    parser_version: str
    parse_status: str = "ready"
    page_count: Optional[int] = None
    quality_score: Optional[float] = None
    plain_text: str = ""
    error_message: Optional[str] = None
    media_asset_id: Optional[str] = None
    media_asset_uri: Optional[str] = None
    media_filename: Optional[str] = None
    media_mime_type: Optional[str] = None
    tables: list = field(default_factory=list)
    facts: list = field(default_factory=list)
    figure_assets: list = field(default_factory=list)
    doc_class: str = ""
    table_count: int = 0


def persist_ingest_artifacts(
    result: IngestPipelineResult,
    user_id: int,
    *,
    plain_text: str | None = None,
) -> None:
    storage = get_storage()
    text = plain_text if plain_text is not None else result.plain_text
    if text:
        storage.save_text(doc_content_key(user_id, result.doc_id), text)
    storage.save_text(
        doc_ndm_key(user_id, result.doc_id),
        json.dumps(result.ndm.to_dict(), ensure_ascii=False, indent=2),
    )
    result.ndm.parse_metadata = {
        **result.ndm.parse_metadata,
        "parser_version": result.parser_version,
        "chunk_count": len(result.chunks),
        "parse_status": result.parse_status,
    }


def chunks_from_ndm_text(text: str, doc_id: str, *, page_hint: str = "") -> list[ChunkRecord]:
    from app.ingestion.chunker import chunk_text

    chunks = chunk_text(text, doc_id)
    if page_hint:
        for c in chunks:
            if not c.page_range:
                c.page_range = page_hint
    return chunks

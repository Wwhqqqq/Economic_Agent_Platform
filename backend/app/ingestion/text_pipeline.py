from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from app.ingestion.chunker import ChunkRecord, build_ndm_from_text, chunk_text
from app.ingestion.ndm import NormalizedDocument
from app.rag.entity_extractor import build_document_title
from app.storage import doc_content_key, doc_ndm_key, get_storage

PARSER_VERSION = "text_pipeline_v1"


@dataclass
class TextIngestResult:
    doc_id: str
    title: str
    ndm: NormalizedDocument
    chunks: list[ChunkRecord]
    ndm_uri: str
    content_uri: str


def prepare_text_ingest(
    content: str,
    doc_id: str,
    user_id: int,
    *,
    filename: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> TextIngestResult:
    """Build NDM + chunks and persist source artifacts to object storage."""
    title = build_document_title(content, doc_id)
    ndm = build_ndm_from_text(content, doc_id, user_id, filename=filename, title=title)
    if metadata:
        ndm.doc_metadata.update(metadata)

    chunks = chunk_text(content, doc_id)
    if not chunks and content.strip():
        chunks = chunk_text(content.strip(), doc_id)

    ndm.parse_metadata = {
        "parser_version": PARSER_VERSION,
        "chunk_count": len(chunks),
        "total_tokens": sum(c.token_count for c in chunks),
    }

    storage = get_storage()
    content_uri = storage.save_text(doc_content_key(user_id, doc_id), content)
    ndm_uri = storage.save_text(doc_ndm_key(user_id, doc_id), json.dumps(ndm.to_dict(), ensure_ascii=False, indent=2))

    return TextIngestResult(
        doc_id=doc_id,
        title=title,
        ndm=ndm,
        chunks=chunks,
        ndm_uri=ndm_uri,
        content_uri=content_uri,
    )


def load_stored_content(user_id: int, doc_id: str) -> str:
    return get_storage().read_text(doc_content_key(user_id, doc_id))

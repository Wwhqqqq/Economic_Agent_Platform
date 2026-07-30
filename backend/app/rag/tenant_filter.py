"""Tenant filters for RAG retrieval — Phase 2 private isolation; Phase 3 extends member branch."""
from __future__ import annotations

from typing import Any, Literal

Visibility = Literal["private", "member"]


def build_user_filter(user_id: int) -> dict[str, Any]:
    """Filter Chroma metadata by user_id (long-term memory, etc.)."""
    return {"user_id": int(user_id)}


def build_private_filter(user_id: int) -> dict[str, Any]:
    """Chroma/Neo4j filter: current user's private documents only."""
    return {
        "$and": [
            {"user_id": int(user_id)},
            {"visibility": "private"},
        ]
    }


def build_retrieval_filter(user_id: int, user_type: str = "regular") -> dict[str, Any]:
    """
    Build metadata filter for hybrid retrieval.

    Phase 2: always private-only for the requesting user.
    Phase 3: extend here — member users OR visibility=member (see docs phase2/04).
    """
    _ = user_type  # reserved for Phase 3 member library branch
    return build_private_filter(user_id)


def knowledge_metadata(
    *,
    doc_id: str,
    user_id: int,
    visibility: Visibility = "private",
    **extra: Any,
) -> dict[str, Any]:
    """Standard Chroma metadata for knowledge documents."""
    meta = {
        "doc_id": doc_id,
        "user_id": int(user_id),
        "visibility": visibility,
        "source": extra.pop("source", "knowledge_upload"),
    }
    meta.update(extra)
    return meta


def chunk_metadata(
    *,
    chunk_id: str,
    doc_id: str,
    user_id: int,
    visibility: Visibility = "private",
    content_type: str = "paragraph",
    section_path: str = "",
    seq: int = 0,
    page_range: str = "",
    **extra: Any,
) -> dict[str, Any]:
    """Standard Chroma metadata for knowledge chunks."""
    meta = {
        "chunk_id": chunk_id,
        "doc_id": doc_id,
        "user_id": int(user_id),
        "visibility": visibility,
        "content_type": content_type,
        "section_path": section_path or "",
        "page_range": page_range or "",
        "seq": int(seq),
        "source": extra.pop("source", "knowledge_chunk"),
    }
    meta.update(extra)
    return meta

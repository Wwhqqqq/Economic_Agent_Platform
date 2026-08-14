"""Seed member knowledge library — ops CLI.

Ingests curated accounting/finance documents with visibility=member into
MySQL + Chroma + Neo4j for member-only RAG retrieval.

Usage:
  python -m scripts.seed_member_knowledge
  python -m scripts.seed_member_knowledge --dir ../data/member_knowledge
  python -m scripts.seed_member_knowledge --force
  python -m scripts.seed_member_knowledge --doc member-cas-framework
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env", override=True)
load_dotenv(override=True)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import session_scope
from app.rag.chunk_store import SYNC_DATABASE_URL
from app.db.models.knowledge import KnowledgeDocument
from app.ingestion.text_pipeline import PARSER_VERSION, prepare_text_ingest
from app.rag.chunk_store import get_chunk_store
from app.rag.hybrid import HybridRetriever
from app.rag.index_router import get_index_router

PLATFORM_USER_ID = 0


def _default_corpus_dir() -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    repo_root = backend_root.parent
    return repo_root / "data" / "member_knowledge"


def _content_fingerprint(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _load_manifest(corpus_dir: Path) -> dict[str, Any]:
    manifest_path = corpus_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _sync_engine():
    from sqlalchemy import create_engine

    return create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)


def _get_member_doc_sync(doc_id: str) -> KnowledgeDocument | None:
    with Session(_sync_engine()) as session:
        return session.get(KnowledgeDocument, doc_id)


def _update_member_doc_sync(
    doc_id: str,
    *,
    title: str,
    filename: str,
    chunk_count: int,
    ndm_uri: str,
    content_uri: str,
    content_hash: str,
    parse_status: str = "ready",
) -> None:
    with Session(_sync_engine()) as session:
        row = session.get(KnowledgeDocument, doc_id)
        if row is None:
            raise RuntimeError(f"document row missing after create: {doc_id}")
        row.title = title
        row.filename = filename
        row.chunk_count = chunk_count
        row.parse_status = parse_status
        row.parser_version = PARSER_VERSION
        row.ndm_uri = ndm_uri
        row.source_type = "text"
        row.mime_type = "text/markdown"
        row.doc_class = "member_corpus"
        # Store content hash in quality_score field for idempotent skip checks
        row.quality_score = float(int(content_hash[:12], 16))
        session.commit()


def _delete_indexes(doc_id: str) -> None:
    retriever = HybridRetriever()
    retriever.delete_knowledge(doc_id, user_id=PLATFORM_USER_ID)


async def _ensure_document_row(doc_id: str, title: str, filename: str) -> None:
    async with session_scope() as db:
        existing = await db.get(KnowledgeDocument, doc_id)
        if existing and existing.deleted_at is None:
            return
        if existing and existing.deleted_at is not None:
            existing.deleted_at = None
            existing.visibility = "member"
            existing.user_id = None
            existing.title = title
            existing.filename = filename
            existing.parse_status = "parsing"
            return
        db.add(
            KnowledgeDocument(
                id=doc_id,
                user_id=None,
                visibility="member",
                title=title,
                filename=filename,
                chunk_count=0,
                parse_status="parsing",
                parser_version=PARSER_VERSION,
                source_type="text",
                mime_type="text/markdown",
                doc_class="member_corpus",
            )
        )


def _ingest_member_file(
    *,
    doc_id: str,
    title: str,
    file_path: Path,
    content: str,
    force: bool,
) -> dict[str, Any]:
    fingerprint = _content_fingerprint(content)
    existing = _get_member_doc_sync(doc_id)

    if existing and existing.deleted_at is None and not force:
        stored_hash = f"{int(existing.quality_score):012x}" if existing.quality_score else ""
        if stored_hash and stored_hash == fingerprint[:12]:
            return {
                "doc_id": doc_id,
                "title": title,
                "status": "skipped",
                "reason": "unchanged",
                "chunks": existing.chunk_count,
            }
        if existing.parse_status == "ready" and existing.chunk_count > 0:
            # Content changed or hash not stored — reindex
            _delete_indexes(doc_id)

    if force and existing and existing.deleted_at is None:
        _delete_indexes(doc_id)

    metadata = {
        "visibility": "member",
        "corpus": "member_knowledge",
        "source_file": file_path.name,
        "content_sha256": fingerprint,
    }
    raw = prepare_text_ingest(
        content,
        doc_id,
        PLATFORM_USER_ID,
        filename=file_path.name,
        metadata=metadata,
    )

    chunk_store = get_chunk_store()
    chunk_store.insert_chunks_sync(raw.chunks, PLATFORM_USER_ID)

    router = get_index_router()
    router.index_document_header(
        doc_id=doc_id,
        title=title,
        user_id=PLATFORM_USER_ID,
        visibility="member",
        sample_text=content[:2000],
    )
    router.index_chunks(
        raw.chunks,
        doc_id=doc_id,
        user_id=PLATFORM_USER_ID,
        visibility="member",
        extra_metadata={"corpus": "member_knowledge", "source_file": file_path.name},
    )

    _update_member_doc_sync(
        doc_id,
        title=raw.title or title,
        filename=file_path.name,
        chunk_count=len(raw.chunks),
        ndm_uri=raw.ndm_uri,
        content_uri=raw.content_uri,
        content_hash=fingerprint,
    )

    return {
        "doc_id": doc_id,
        "title": raw.title or title,
        "status": "indexed",
        "chunks": len(raw.chunks),
        "file": file_path.name,
    }


async def seed_corpus(
    corpus_dir: Path,
    *,
    force: bool = False,
    doc_filter: str | None = None,
) -> list[dict[str, Any]]:
    manifest = _load_manifest(corpus_dir)
    documents = manifest.get("documents", [])
    results: list[dict[str, Any]] = []

    for entry in documents:
        doc_id = entry["doc_id"]
        if doc_filter and doc_id != doc_filter:
            continue

        rel_file = entry["file"]
        file_path = corpus_dir / rel_file
        if not file_path.is_file():
            results.append(
                {
                    "doc_id": doc_id,
                    "title": entry.get("title", doc_id),
                    "status": "failed",
                    "reason": f"missing file: {rel_file}",
                }
            )
            continue

        content = file_path.read_text(encoding="utf-8")
        title = entry.get("title", doc_id)

        await _ensure_document_row(doc_id, title, file_path.name)
        result = _ingest_member_file(
            doc_id=doc_id,
            title=title,
            file_path=file_path,
            content=content,
            force=force,
        )
        results.append(result)

    return results


def _print_summary(results: list[dict[str, Any]], corpus_dir: Path) -> None:
    indexed = sum(1 for r in results if r.get("status") == "indexed")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    failed = sum(1 for r in results if r.get("status") == "failed")
    total_chunks = sum(r.get("chunks", 0) for r in results if r.get("status") in {"indexed", "skipped"})

    print("\n=== Member Knowledge Seed Summary ===")
    print(f"Corpus dir : {corpus_dir}")
    print(f"Indexed    : {indexed}")
    print(f"Skipped    : {skipped}")
    print(f"Failed     : {failed}")
    print(f"Chunks     : {total_chunks}")
    print("\nDetails:")
    for row in results:
        status = row.get("status")
        extra = f" ({row.get('reason')})" if row.get("reason") else ""
        chunks = row.get("chunks", 0)
        print(f"  [{status}] {row.get('doc_id')} — {row.get('title')} — {chunks} chunks{extra}")


async def main(args: argparse.Namespace) -> None:
    corpus_dir = Path(args.dir).resolve()
    if not corpus_dir.is_dir():
        print(f"Corpus directory not found: {corpus_dir}")
        sys.exit(1)

    results = await seed_corpus(corpus_dir, force=args.force, doc_filter=args.doc)
    _print_summary(results, corpus_dir)

    if any(r.get("status") == "failed" for r in results):
        sys.exit(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed member-only knowledge library")
    parser.add_argument(
        "--dir",
        default=str(_default_corpus_dir()),
        help="Path to member_knowledge corpus directory",
    )
    parser.add_argument("--force", action="store_true", help="Re-index even if content unchanged")
    parser.add_argument("--doc", default=None, help="Seed only one doc_id from manifest")
    asyncio.run(main(parser.parse_args()))

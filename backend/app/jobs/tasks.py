from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import DATABASE_URL
from app.db.models.ingest_job import IngestJob
from app.db.models.knowledge import KnowledgeDocument
from app.ingestion.media.service import MediaAssetService, prepare_media_ingest
from app.ingestion.pdf.pipeline import prepare_pdf_ingest
from app.ingestion.pipeline_common import IngestPipelineResult
from app.ingestion.text_pipeline import PARSER_VERSION as TEXT_PARSER_VERSION
from app.ingestion.text_pipeline import load_stored_content, prepare_text_ingest
from app.rag.chunk_store import get_chunk_store
from app.rag.index_router import get_index_router
from app.storage import doc_ndm_key, doc_source_key, get_storage

SYNC_DATABASE_URL = DATABASE_URL.replace("+aiomysql", "+pymysql")
_sync_engine = None


def _engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)
    return _sync_engine


def _mark_job_started(doc_id: str, job_id: str) -> bool:
    now = datetime.now(timezone.utc)
    with Session(_engine()) as session:
        doc = session.get(KnowledgeDocument, doc_id)
        job = session.get(IngestJob, job_id)
        if not doc or not job:
            return False
        doc.parse_status = "parsing"
        job.status = "parsing"
        job.started_at = now
        session.commit()
    return True


def _finalize_failure(doc_id: str, job_id: str, error: str) -> None:
    with Session(_engine()) as session:
        doc = session.get(KnowledgeDocument, doc_id)
        job = session.get(IngestJob, job_id)
        if doc:
            doc.parse_status = "failed"
        if job:
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            job.error_message = error[:2000]
        session.commit()


def _index_result(result: IngestPipelineResult, user_id: int) -> dict:
    if result.parse_status != "ready" or not result.chunks:
        meta = {"chunks_indexed": 0, "entities_extracted": 0, "skipped": True}
        if result.tables or result.facts:
            index_router = get_index_router()
            meta.update(index_router.index_tables_and_facts(
                doc_id=result.doc_id, user_id=user_id,
                tables=result.tables, facts=result.facts,
            ))
        return meta

    chunk_store = get_chunk_store()
    index_router = get_index_router()
    chunk_store.insert_chunks_sync(result.chunks, user_id)
    sample = result.plain_text[:2000] if result.plain_text else result.title
    index_router.index_document_header(
        doc_id=result.doc_id,
        title=result.title,
        user_id=user_id,
        visibility="private",
        sample_text=sample,
    )
    rag_meta = index_router.index_chunks(
        result.chunks,
        doc_id=result.doc_id,
        user_id=user_id,
        visibility="private",
    )
    if result.tables or result.facts:
        rag_meta.update(index_router.index_tables_and_facts(
            doc_id=result.doc_id, user_id=user_id,
            tables=result.tables, facts=result.facts,
        ))
    return rag_meta


def _persist_media_asset(result: IngestPipelineResult, user_id: int) -> None:
    import json as json_lib

    assets_to_persist = []
    if result.media_asset_id:
        meta = result.ndm.parse_metadata or {}
        assets_to_persist.append({
            "asset_id": result.media_asset_id,
            "doc_id": result.doc_id,
            "filename": result.media_filename or "image.png",
            "mime_type": result.media_mime_type or "application/octet-stream",
            "storage_uri": result.media_asset_uri or result.content_uri,
            "source": "upload",
            "image_class": meta.get("image_class"),
            "ocr_text": result.plain_text or None,
            "ocr_quality": result.quality_score,
            "ocr_engine": meta.get("ocr_engine"),
            "width": meta.get("width"),
            "height": meta.get("height"),
            "vlm_caption": meta.get("vlm_caption"),
            "vlm_structured": meta.get("vlm_structured"),
            "vlm_quality": meta.get("vlm_quality"),
            "vlm_engine": meta.get("vlm_engine"),
            "parse_status": result.parse_status,
        })
    for parsed in getattr(result, "figure_assets", []) or []:
        assets_to_persist.append({
            "asset_id": parsed.asset_id,
            "doc_id": result.doc_id,
            "filename": parsed.filename,
            "mime_type": parsed.mime_type,
            "storage_uri": parsed.storage_uri,
            "source": "pdf_extract",
            "image_class": parsed.image_class,
            "ocr_text": parsed.ocr_text,
            "ocr_quality": parsed.ocr_quality,
            "ocr_engine": parsed.ocr_engine,
            "width": parsed.width,
            "height": parsed.height,
            "thumbnail_uri": parsed.thumbnail_uri,
            "vlm_caption": parsed.vlm_caption,
            "vlm_structured": json_lib.dumps(parsed.vlm_structured, ensure_ascii=False) if parsed.vlm_structured else None,
            "vlm_quality": parsed.vlm_quality,
            "vlm_engine": parsed.vlm_engine,
            "content_hash": parsed.content_hash,
            "parse_status": parsed.parse_status,
            "page_no": parsed.page_no,
            "bbox": parsed.bbox,
        })
    if not assets_to_persist:
        return
    with Session(_engine()) as session:
        svc = MediaAssetService()
        for item in assets_to_persist:
            svc.persist_record_sync(session, user_id=user_id, **item)
        session.commit()


def _run_ingest(
    doc_id: str,
    job_id: str,
    user_id: int,
    prepare_fn: Callable[[], IngestPipelineResult],
) -> dict:
    if not _mark_job_started(doc_id, job_id):
        return {"doc_id": doc_id, "status": "failed", "error": "document or job not found"}
    try:
        result = prepare_fn()
        if result.media_asset_id or getattr(result, "figure_assets", None):
            _persist_media_asset(result, user_id)
        rag_meta = _index_result(result, user_id)
        with Session(_engine()) as session:
            doc = session.get(KnowledgeDocument, doc_id)
            job = session.get(IngestJob, job_id)
            finished = datetime.now(timezone.utc)
            if doc:
                doc.title = result.title
                doc.chunk_count = len(result.chunks)
                doc.parse_status = result.parse_status
                doc.parser_version = result.parser_version
                doc.quality_score = result.quality_score
                doc.page_count = result.page_count
                doc.ndm_uri = doc_ndm_key(user_id, doc_id)
                if hasattr(doc, "doc_class"):
                    doc.doc_class = result.doc_class or (result.ndm.doc_metadata.get("doc_class") if result.ndm else None)
                if hasattr(doc, "table_count"):
                    doc.table_count = result.table_count or len(result.tables or [])
            if job:
                job.status = "ready" if result.parse_status == "ready" else result.parse_status
                job.finished_at = finished
                job.error_message = result.error_message
            session.commit()
        return {
            "doc_id": doc_id,
            "status": result.parse_status,
            "chunk_count": len(result.chunks),
            **rag_meta,
        }
    except Exception as exc:
        err = traceback.format_exc()
        print(f"[ingest] failed doc={doc_id}: {err}")
        _finalize_failure(doc_id, job_id, str(exc))
        return {"doc_id": doc_id, "status": "failed", "error": str(exc)}


def run_text_ingest(doc_id: str, job_id: str, user_id: int, *, filename: str | None = None) -> dict:
    def _prepare() -> IngestPipelineResult:
        content = load_stored_content(user_id, doc_id)
        raw = prepare_text_ingest(content, doc_id, user_id, filename=filename)
        return IngestPipelineResult(
            doc_id=raw.doc_id,
            title=raw.title,
            ndm=raw.ndm,
            chunks=raw.chunks,
            ndm_uri=raw.ndm_uri,
            content_uri=raw.content_uri,
            parser_version=TEXT_PARSER_VERSION,
            parse_status="ready",
            quality_score=min(1.0, len(raw.chunks) / max(1, len(content) // 1200)),
            plain_text=content,
        )

    return _run_ingest(doc_id, job_id, user_id, _prepare)


def run_pdf_ingest(doc_id: str, job_id: str, user_id: int, *, filename: str | None = None) -> dict:
    def _prepare() -> IngestPipelineResult:
        storage = get_storage()
        for ext in (".pdf", ".PDF", ".Pdf"):
            key = doc_source_key(user_id, doc_id, ext.lower() if ext != ".PDF" else ".pdf")
            if storage.exists(key):
                return prepare_pdf_ingest(storage.read_bytes(key), doc_id, user_id, filename=filename)
        key = doc_source_key(user_id, doc_id, ".pdf")
        if storage.exists(key):
            return prepare_pdf_ingest(storage.read_bytes(key), doc_id, user_id, filename=filename)
        raise FileNotFoundError("PDF source file not found in object storage")

    return _run_ingest(doc_id, job_id, user_id, _prepare)


def run_media_ingest(doc_id: str, job_id: str, user_id: int, *, filename: str | None = None) -> dict:
    def _prepare() -> IngestPipelineResult:
        storage = get_storage()
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
            key = doc_source_key(user_id, doc_id, ext)
            if storage.exists(key):
                return prepare_media_ingest(
                    storage.read_bytes(key),
                    doc_id,
                    user_id,
                    filename=filename or f"image{ext}",
                )
        raise FileNotFoundError("Image source file not found in object storage")

    return _run_ingest(doc_id, job_id, user_id, _prepare)

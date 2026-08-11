"""Knowledge document service — MySQL metadata + async chunk ingest."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ingest_job import IngestJob
from app.db.models.knowledge import KnowledgeDocument
from app.ingestion.media.service import IMAGE_EXTENSIONS
from app.ingestion.text_pipeline import PARSER_VERSION
from app.rag.entity_extractor import build_document_title
from app.rag.service import get_hybrid_retriever
from app.schemas.user_context import UserContext
from app.storage import doc_content_key, doc_object_prefix, doc_source_key, get_storage

UPLOAD_ROOT = os.path.join("data", "uploads")

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS_ALL = IMAGE_EXTENSIONS


def _file_ext(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def detect_upload_kind(filename: str) -> str:
    ext = _file_ext(filename)
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in IMAGE_EXTENSIONS_ALL:
        return "image"
    if ext in TEXT_EXTENSIONS:
        return "text"
    return "binary"


def job_type_for_kind(kind: str) -> str:
    return {
        "pdf": "pdf_ingest",
        "image": "media_ingest",
        "text": "text_ingest",
    }.get(kind, "text_ingest")


def user_upload_dir(user_id: int) -> str:
    path = os.path.join(UPLOAD_ROOT, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path


async def count_user_documents(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(
            KnowledgeDocument.user_id == user_id,
            KnowledgeDocument.visibility == "private",
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    return int(result.scalar() or 0)


async def get_owned_document(
    db: AsyncSession, doc_id: str, user_id: int
) -> Optional[KnowledgeDocument]:
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.user_id == user_id,
            KnowledgeDocument.visibility == "private",
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_member_documents(
    db: AsyncSession, *, limit: int = 100, offset: int = 0
) -> list[KnowledgeDocument]:
    result = await db.execute(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.visibility == "member",
            KnowledgeDocument.deleted_at.is_(None),
        )
        .order_by(KnowledgeDocument.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def count_member_documents(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(
            KnowledgeDocument.visibility == "member",
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    return int(result.scalar() or 0)


async def list_user_documents(
    db: AsyncSession, user_id: int, *, limit: int = 100, offset: int = 0
) -> list[KnowledgeDocument]:
    result = await db.execute(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.user_id == user_id,
            KnowledgeDocument.visibility == "private",
            KnowledgeDocument.deleted_at.is_(None),
        )
        .order_by(KnowledgeDocument.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_latest_ingest_job(db: AsyncSession, doc_id: str) -> Optional[IngestJob]:
    result = await db.execute(
        select(IngestJob)
        .where(IngestJob.doc_id == doc_id)
        .order_by(IngestJob.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _create_document_job(
    db: AsyncSession,
    user: UserContext,
    *,
    doc_id: str,
    title: str,
    filename: str | None,
    source_type: str,
    mime_type: str | None,
    job_type: str,
) -> dict:
    job_id = str(uuid.uuid4())
    row = KnowledgeDocument(
        id=doc_id,
        user_id=user.user_id,
        visibility="private",
        title=title,
        filename=filename,
        chunk_count=0,
        parse_status="parsing",
        parser_version=PARSER_VERSION,
        source_type=source_type,
        mime_type=mime_type,
    )
    db.add(row)
    job = IngestJob(
        id=job_id,
        doc_id=doc_id,
        user_id=user.user_id,
        job_type=job_type,
        status="pending",
    )
    db.add(job)
    await db.flush()
    return {
        "doc_id": doc_id,
        "job_id": job_id,
        "title": title,
        "visibility": "private",
        "status": "parsing",
        "parse_status": "parsing",
        "source_type": source_type,
        "job_type": job_type,
        "filename": filename,
    }


async def prepare_text_upload(
    db: AsyncSession,
    user: UserContext,
    content: str,
    *,
    doc_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    filename: Optional[str] = None,
) -> dict:
    if user.user_id == 0:
        raise PermissionError("未登录")

    doc_id = doc_id or str(uuid.uuid4())
    title = build_document_title(content, doc_id)
    storage = get_storage()
    content_uri = storage.save_text(doc_content_key(user.user_id, doc_id), content)

    result = await _create_document_job(
        db,
        user,
        doc_id=doc_id,
        title=title,
        filename=filename,
        source_type="text",
        mime_type="text/plain",
        job_type="text_ingest",
    )
    result["content_uri"] = content_uri
    result["metadata"] = metadata or {}
    return result


async def prepare_binary_upload(
    db: AsyncSession,
    user: UserContext,
    raw: bytes,
    *,
    filename: str,
    metadata: Optional[dict] = None,
) -> dict:
    if user.user_id == 0:
        raise PermissionError("未登录")

    kind = detect_upload_kind(filename)
    ext = _file_ext(filename) or ".bin"
    doc_id = str(uuid.uuid4())
    storage = get_storage()

    if kind == "text":
        content = raw.decode("utf-8", errors="replace")
        return await prepare_text_upload(db, user, content, doc_id=doc_id, metadata=metadata, filename=filename)

    source_uri = storage.save_bytes(doc_source_key(user.user_id, doc_id, ext), raw)
    title = os.path.basename(filename) or f"Document {doc_id[:8]}"
    mime_map = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    result = await _create_document_job(
        db,
        user,
        doc_id=doc_id,
        title=title,
        filename=filename,
        source_type=kind if kind in ("pdf", "image") else "binary",
        mime_type=mime_map.get(ext),
        job_type=job_type_for_kind(kind),
    )
    result["content_uri"] = source_uri
    result["metadata"] = metadata or {}
    return result


async def get_document_status(db: AsyncSession, user: UserContext, doc_id: str) -> dict:
    row = await get_owned_document(db, doc_id, user.user_id)
    if not row:
        raise LookupError("文档不存在或无权访问")

    job = await get_latest_ingest_job(db, doc_id)
    return {
        "doc_id": row.id,
        "title": row.title,
        "parse_status": row.parse_status,
        "chunk_count": row.chunk_count,
        "parser_version": row.parser_version,
        "quality_score": row.quality_score,
        "ndm_uri": row.ndm_uri,
        "page_count": row.page_count,
        "source_type": getattr(row, "source_type", "text"),
        "job_id": job.id if job else None,
        "job_status": job.status if job else row.parse_status,
        "job_type": job.job_type if job else None,
        "error_message": job.error_message if job else None,
        "started_at": job.started_at.isoformat() if job and job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job and job.finished_at else None,
    }


async def upload_text(
    db: AsyncSession,
    user: UserContext,
    content: str,
    *,
    doc_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    entities: Optional[list] = None,
    filename: Optional[str] = None,
) -> dict:
    _ = entities
    return await prepare_text_upload(
        db,
        user,
        content,
        doc_id=doc_id,
        metadata=metadata,
        filename=filename,
    )


async def save_upload_file(user_id: int, filename: str, raw: bytes) -> str:
    safe_name = os.path.basename(filename or "upload.txt")
    dest_dir = user_upload_dir(user_id)
    dest_path = os.path.join(dest_dir, safe_name)
    with open(dest_path, "wb") as f:
        f.write(raw)
    return dest_path


async def soft_delete_document(db: AsyncSession, user: UserContext, doc_id: str) -> dict:
    row = await get_owned_document(db, doc_id, user.user_id)
    if not row:
        raise LookupError("文档不存在或无权删除")

    row.deleted_at = datetime.now(timezone.utc)
    await db.flush()

    result = get_hybrid_retriever().delete_knowledge(doc_id, user_id=user.user_id)
    try:
        get_storage().delete_prefix(doc_object_prefix(user.user_id, doc_id))
    except Exception:
        pass
    return {"doc_id": doc_id, "status": "deleted", **result}

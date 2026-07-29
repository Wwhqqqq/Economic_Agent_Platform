"""Knowledge document service — MySQL metadata + RAG vector/graph sync."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import KnowledgeDocument
from app.rag.entity_extractor import build_document_title
from app.rag.service import get_hybrid_retriever
from app.schemas.user_context import UserContext

UPLOAD_ROOT = os.path.join("data", "uploads")


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
    if user.user_id == 0:
        raise PermissionError("未登录")

    # TODO(phase3): await check_quota("document", user.user_id, user.user_type)

    doc_id = doc_id or str(uuid.uuid4())
    title = build_document_title(content, doc_id)
    meta = metadata or {}

    row = KnowledgeDocument(
        id=doc_id,
        user_id=user.user_id,
        visibility="private",
        title=title,
        filename=filename,
        chunk_count=1,
    )
    db.add(row)
    await db.flush()

    rag_result = get_hybrid_retriever().add_knowledge(
        content=content,
        doc_id=doc_id,
        user_id=user.user_id,
        metadata={**meta, "filename": filename} if filename else meta,
        entities=entities,
        visibility="private",
    )
    return {"doc_id": doc_id, "title": title, "visibility": "private", **rag_result}


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

    get_hybrid_retriever().delete_knowledge(doc_id, user_id=user.user_id)
    return {"doc_id": doc_id, "status": "deleted"}

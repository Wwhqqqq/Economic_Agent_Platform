"""知识库管理 API"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File

from app.core.database import get_db
from app.jobs.tasks import run_media_ingest, run_pdf_ingest, run_text_ingest
from app.models.settings import KnowledgeUpload, KnowledgeSearch
from app.rag.service import get_hybrid_retriever
from app.schemas.user_context import UserContext
from app.services.audit_log import log_action
from app.services.auth import AUTH_ENABLED, get_current_user
from app.services import knowledge_service
from app.services.quota_service import QuotaExceededError, check_quota, quota_http_exception
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _require_logged_in(user: UserContext) -> None:
    if AUTH_ENABLED and user.user_id == 0:
        raise HTTPException(status_code=401, detail="未登录")


def _enqueue_ingest(
    background_tasks: BackgroundTasks,
    *,
    job_type: str,
    doc_id: str,
    job_id: str,
    user_id: int,
    filename: str | None = None,
) -> None:
    runners = {
        "text_ingest": run_text_ingest,
        "pdf_ingest": run_pdf_ingest,
        "media_ingest": run_media_ingest,
    }
    fn = runners.get(job_type, run_text_ingest)
    background_tasks.add_task(fn, doc_id, job_id, user_id, filename=filename)


@router.post("/upload")
async def upload_knowledge(
    req: KnowledgeUpload,
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    try:
        await check_quota(db, "upload_document", user.user_id, user.user_type)
    except QuotaExceededError as exc:
        raise quota_http_exception(exc) from exc
    try:
        result = await knowledge_service.upload_text(
            db,
            user,
            req.content,
            doc_id=req.doc_id,
            metadata=req.metadata,
            entities=req.entities,
        )
        await db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _enqueue_ingest(
        background_tasks,
        job_type="text_ingest",
        doc_id=result["doc_id"],
        job_id=result["job_id"],
        user_id=user.user_id,
    )
    log_action("knowledge.upload", user.username, {"doc_id": result["doc_id"]})
    return {"status": "parsing", **result}


@router.post("/upload/file")
async def upload_knowledge_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    raw = await file.read()
    try:
        await check_quota(
            db, "upload_document", user.user_id, user.user_type, file_size_bytes=len(raw)
        )
    except QuotaExceededError as exc:
        raise quota_http_exception(exc) from exc
    await knowledge_service.save_upload_file(user.user_id, file.filename or "upload.bin", raw)
    try:
        result = await knowledge_service.prepare_binary_upload(
            db,
            user,
            raw,
            filename=file.filename or "upload.bin",
            metadata={"source": file.filename or "upload", "filename": file.filename},
        )
        await db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _enqueue_ingest(
        background_tasks,
        job_type=result.get("job_type", "text_ingest"),
        doc_id=result["doc_id"],
        job_id=result["job_id"],
        user_id=user.user_id,
        filename=file.filename,
    )
    log_action(
        "knowledge.upload_file",
        user.username,
        {"doc_id": result["doc_id"], "filename": file.filename, "job_type": result.get("job_type")},
    )
    return {"status": "parsing", "filename": file.filename, **result}


@router.post("/upload/media")
async def upload_knowledge_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dedicated image upload endpoint (png/jpg/webp)."""
    _require_logged_in(user)
    filename = file.filename or "image.png"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("png", "jpg", "jpeg", "webp", "gif", "bmp"):
        raise HTTPException(status_code=400, detail="仅支持 png/jpg/jpeg/webp/gif/bmp 图片")

    raw = await file.read()
    try:
        result = await knowledge_service.prepare_binary_upload(
            db,
            user,
            raw,
            filename=filename,
            metadata={"source": "media_upload", "filename": filename},
        )
        await db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _enqueue_ingest(
        background_tasks,
        job_type="media_ingest",
        doc_id=result["doc_id"],
        job_id=result["job_id"],
        user_id=user.user_id,
        filename=filename,
    )
    return {"status": "parsing", "filename": filename, **result}


@router.get("/documents/member")
async def list_member_library(
    limit: int = 100,
    offset: int = 0,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    if not user.is_member:
        raise HTTPException(
            status_code=403,
            detail={"code": "MEMBERSHIP_REQUIRED", "message": "会员专享知识库需开通会员"},
        )
    rows = await knowledge_service.list_member_documents(db, limit=limit, offset=offset)
    documents = [
        {
            "doc_id": row.id,
            "title": row.title,
            "filename": row.filename,
            "visibility": row.visibility,
            "parse_status": row.parse_status,
            "chunk_count": row.chunk_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    total = await knowledge_service.count_member_documents(db)
    return {"documents": documents, "total": total}


@router.get("/documents")
async def list_documents(
    limit: int = 100,
    offset: int = 0,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    rows = await knowledge_service.list_user_documents(db, user.user_id, limit=limit, offset=offset)
    hybrid = get_hybrid_retriever()
    preview_by_id: dict[str, str] = {}
    stats: dict = {}
    try:
        chroma_docs = hybrid.list_documents(
            limit=limit, offset=offset, user_id=user.user_id, user_type=user.user_type
        )
        preview_by_id = {d["doc_id"]: d.get("preview", "") for d in chroma_docs}
        stats = hybrid.stats(user_id=user.user_id, user_type=user.user_type)
    except Exception as exc:
        print(f"[Knowledge] vector index unavailable, returning MySQL rows only: {exc}")
        stats = {
            "vector_docs": 0,
            "graph_entities": 0,
            "graph_documents": 0,
            "graph_available": hybrid.graph_retriever.available,
            "vector_degraded": True,
        }
    documents = [
        {
            "doc_id": row.id,
            "title": row.title,
            "filename": row.filename,
            "visibility": row.visibility,
            "parse_status": row.parse_status,
            "chunk_count": row.chunk_count,
            "source_type": getattr(row, "source_type", "text"),
            "page_count": row.page_count,
            "doc_class": getattr(row, "doc_class", None),
            "table_count": getattr(row, "table_count", 0),
            "quality_score": row.quality_score,
            "preview": preview_by_id.get(row.id, row.title),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    total = await knowledge_service.count_user_documents(db, user.user_id)
    return {"documents": documents, "total": total, **stats}


@router.get("/documents/{doc_id}/status")
async def document_status(
    doc_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    try:
        return await knowledge_service.get_document_status(db, user, doc_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    try:
        result = await knowledge_service.soft_delete_document(db, user, doc_id)
        await db.commit()
    except LookupError:
        raise HTTPException(status_code=403, detail="文档不存在或无权删除")
    log_action("knowledge.delete", user.username, {"doc_id": doc_id})
    return result


@router.post("/search")
async def search_knowledge(
    req: KnowledgeSearch,
    user: UserContext = Depends(get_current_user),
):
    _require_logged_in(user)
    tier = "member" if user.is_member else "regular"
    docs = get_hybrid_retriever().retrieve(
        query=req.query,
        top_k=req.top_k,
        mode=req.mode,
        user_id=user.user_id,
        user_type=tier,
    )
    return {
        "query": req.query,
        "mode": req.mode,
        "results": [
            {
                "content": doc.page_content[:500],
                "metadata": doc.metadata,
            }
            for doc in docs
        ],
    }


@router.get("/stats")
async def knowledge_stats(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    stats = get_hybrid_retriever().stats(user_id=user.user_id, user_type=user.user_type)
    stats["mysql_docs"] = await knowledge_service.count_user_documents(db, user.user_id)
    return stats

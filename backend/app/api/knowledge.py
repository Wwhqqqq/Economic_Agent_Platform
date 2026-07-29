"""知识库管理 API"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.core.database import get_db
from app.models.settings import KnowledgeUpload, KnowledgeSearch
from app.rag.service import get_hybrid_retriever
from app.schemas.user_context import UserContext
from app.services.audit_log import log_action
from app.services.auth import AUTH_ENABLED, get_current_user
from app.services import knowledge_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _require_logged_in(user: UserContext) -> None:
    if AUTH_ENABLED and user.user_id == 0:
        raise HTTPException(status_code=401, detail="未登录")


@router.post("/upload")
async def upload_knowledge(
    req: KnowledgeUpload,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    try:
        result = await knowledge_service.upload_text(
            db,
            user,
            req.content,
            doc_id=req.doc_id,
            metadata=req.metadata,
            entities=req.entities,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    log_action("knowledge.upload", user.username, {"doc_id": result["doc_id"]})
    return {"status": "uploaded", **result}


@router.post("/upload/file")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    raw = await file.read()
    await knowledge_service.save_upload_file(user.user_id, file.filename or "upload.txt", raw)
    content = raw.decode("utf-8", errors="replace")
    try:
        result = await knowledge_service.upload_text(
            db,
            user,
            content,
            metadata={"source": file.filename or "upload", "filename": file.filename},
            filename=file.filename,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    log_action(
        "knowledge.upload_file",
        user.username,
        {"doc_id": result["doc_id"], "filename": file.filename},
    )
    return {"status": "uploaded", "filename": file.filename, **result}


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
    chroma_docs = hybrid.list_documents(
        limit=limit, offset=offset, user_id=user.user_id, user_type=user.user_type
    )
    preview_by_id = {d["doc_id"]: d.get("preview", "") for d in chroma_docs}
    documents = [
        {
            "doc_id": row.id,
            "title": row.title,
            "filename": row.filename,
            "visibility": row.visibility,
            "preview": preview_by_id.get(row.id, row.title),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    stats = hybrid.stats(user_id=user.user_id, user_type=user.user_type)
    total = await knowledge_service.count_user_documents(db, user.user_id)
    return {"documents": documents, "total": total, **stats}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_logged_in(user)
    try:
        result = await knowledge_service.soft_delete_document(db, user, doc_id)
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
    docs = get_hybrid_retriever().retrieve(
        query=req.query,
        top_k=req.top_k,
        mode=req.mode,
        user_id=user.user_id,
        user_type=user.user_type,
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

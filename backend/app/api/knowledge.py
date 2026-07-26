"""知识库管理 API"""
import uuid
from fastapi import APIRouter, UploadFile, File, Depends

from app.models.settings import KnowledgeUpload, KnowledgeSearch
from app.rag.service import get_hybrid_retriever
from app.services.audit_log import log_action
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/upload")
async def upload_knowledge(req: KnowledgeUpload, user: str = Depends(get_current_user)):
    doc_id = req.doc_id or str(uuid.uuid4())
    result = get_hybrid_retriever().add_knowledge(
        content=req.content,
        doc_id=doc_id,
        metadata=req.metadata,
        entities=req.entities,
    )
    log_action("knowledge.upload", user, {"doc_id": doc_id})
    return {"status": "uploaded", **result}


@router.post("/upload/file")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    user: str = Depends(get_current_user),
):
    content = (await file.read()).decode("utf-8", errors="replace")
    doc_id = str(uuid.uuid4())
    result = get_hybrid_retriever().add_knowledge(
        content=content,
        doc_id=doc_id,
        metadata={"source": file.filename or "upload", "filename": file.filename},
    )
    log_action("knowledge.upload_file", user, {"doc_id": doc_id, "filename": file.filename})
    return {"status": "uploaded", "filename": file.filename, **result}


@router.get("/documents")
async def list_documents(limit: int = 100, offset: int = 0):
    docs = get_hybrid_retriever().list_documents(limit=limit, offset=offset)
    stats = get_hybrid_retriever().stats()
    return {"documents": docs, "total": stats.get("vector_docs", len(docs)), **stats}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, user: str = Depends(get_current_user)):
    result = get_hybrid_retriever().delete_knowledge(doc_id)
    log_action("knowledge.delete", user, {"doc_id": doc_id})
    return result


@router.post("/search")
async def search_knowledge(req: KnowledgeSearch):
    docs = get_hybrid_retriever().retrieve(
        query=req.query,
        top_k=req.top_k,
        mode=req.mode,
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
async def knowledge_stats():
    return get_hybrid_retriever().stats()

"""RAG 服务单例 — 全局共享 HybridRetriever 实例"""
from app.rag.hybrid import HybridRetriever

_hybrid_retriever: HybridRetriever | None = None


def get_hybrid_retriever() -> HybridRetriever:
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever

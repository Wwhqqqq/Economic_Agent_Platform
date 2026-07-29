"""
向量存储检索器
基于 ChromaDB 的语义相似度检索
"""
from typing import Optional
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.db.chroma import get_chroma_client
from app.rag.tenant_filter import build_retrieval_filter, knowledge_metadata


KNOWLEDGE_COLLECTION = "knowledge_base"


class VectorStoreRetriever:
    """向量存储检索器"""

    def __init__(self):
        self._chroma = get_chroma_client()

    def add_document(
        self,
        content: str,
        doc_id: str,
        metadata: dict = None,
        *,
        user_id: int | None = None,
        visibility: str = "private",
    ) -> None:
        meta = metadata or {}
        if user_id is not None:
            meta = knowledge_metadata(
                doc_id=doc_id,
                user_id=user_id,
                visibility=visibility,  # type: ignore[arg-type]
                **{k: v for k, v in meta.items() if k not in ("doc_id", "user_id", "visibility")},
            )
        self._chroma.add_documents(
            collection_name=KNOWLEDGE_COLLECTION,
            ids=[doc_id],
            documents=[content],
            metadatas=[meta],
        )

    def add_documents(
        self,
        contents: list[str],
        ids: list[str],
        metadatas: list[dict] = None,
    ) -> None:
        if not contents:
            return
        base_meta = [{} for _ in contents]
        if metadatas:
            for i, m in enumerate(metadatas):
                base_meta[i].update(m)

        self._chroma.add_documents(
            collection_name=KNOWLEDGE_COLLECTION,
            ids=ids,
            documents=contents,
            metadatas=base_meta,
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: dict = None,
        *,
        user_id: int | None = None,
        user_type: str = "regular",
    ) -> list[Document]:
        where = metadata_filter
        if user_id is not None and where is None:
            where = build_retrieval_filter(user_id, user_type)

        results = self._chroma.query(
            collection_name=KNOWLEDGE_COLLECTION,
            query_texts=[query],
            n_results=top_k,
            where=where,
        )

        documents = []
        if results.get("documents") and results["documents"][0]:
            for i, doc_text in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                doc_id = results["ids"][0][i] if results.get("ids") else f"doc_{i}"

                documents.append(
                    Document(
                        page_content=doc_text,
                        metadata={
                            **meta,
                            "doc_id": doc_id,
                            "score": 1 - distance,
                            "source": "vector",
                        },
                    )
                )

        return documents

    def retrieve_with_scores(self, query: str, top_k: int = 5, **kwargs) -> list[dict]:
        docs = self.retrieve(query, top_k, **kwargs)
        return [
            {
                "content": doc.page_content,
                "score": doc.metadata.get("score", 0),
                "metadata": doc.metadata,
            }
            for doc in docs
        ]

    def as_retriever(self, top_k: int = 5):
        def _retrieve(query: str):
            return self.retrieve(query, top_k)
        return RunnableLambda(_retrieve)

    def count(self, user_id: int | None = None, user_type: str = "regular") -> int:
        if user_id is None:
            return self._chroma.count(KNOWLEDGE_COLLECTION)
        where = build_retrieval_filter(user_id, user_type)
        return self._chroma.count_where(KNOWLEDGE_COLLECTION, where)

    def delete(self, doc_id: str) -> None:
        self._chroma.delete(KNOWLEDGE_COLLECTION, [doc_id])

    def list_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        *,
        user_id: int | None = None,
        user_type: str = "regular",
    ) -> list[dict]:
        where = build_retrieval_filter(user_id, user_type) if user_id is not None else None
        raw = self._chroma.get_all(KNOWLEDGE_COLLECTION, limit=limit, offset=offset, where=where)
        docs = []
        ids = raw.get("ids") or []
        documents = raw.get("documents") or []
        metadatas = raw.get("metadatas") or []
        for i, doc_id in enumerate(ids):
            content = documents[i] if i < len(documents) else ""
            meta = metadatas[i] if i < len(metadatas) else {}
            docs.append({
                "doc_id": doc_id,
                "preview": (content or "")[:200],
                "metadata": meta,
                "visibility": meta.get("visibility", "private"),
            })
        return docs

"""
向量存储检索器
基于 ChromaDB 的语义相似度检索

支持：
- 文档分块与向量化
- 语义相似度检索
- 元数据过滤
- 作为 LangChain Retriever 使用
"""
from typing import Optional
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.db.chroma import get_chroma_client


KNOWLEDGE_COLLECTION = "knowledge_base"


class VectorStoreRetriever:
    """
    向量存储检索器

    LCEL 集成示例:
        retriever = VectorStoreRetriever()
        chain = (
            {"query": RunnablePassthrough()}
            | RunnableLambda(retriever.retrieve)
            | prompt
            | llm
        )
    """

    def __init__(self):
        self._chroma = get_chroma_client()

    def add_document(
        self,
        content: str,
        doc_id: str,
        metadata: dict = None,
    ) -> None:
        """添加单个文档到知识库"""
        self._chroma.add_documents(
            collection_name=KNOWLEDGE_COLLECTION,
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata or {}],
        )

    def add_documents(
        self,
        contents: list[str],
        ids: list[str],
        metadatas: list[dict] = None,
    ) -> None:
        """批量添加文档"""
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
    ) -> list[Document]:
        """
        向量检索

        Args:
            query: 查询文本
            top_k: 返回文档数
            metadata_filter: 元数据过滤条件

        Returns:
            LangChain Document 列表
        """
        results = self._chroma.query(
            collection_name=KNOWLEDGE_COLLECTION,
            query_texts=[query],
            n_results=top_k,
            where=metadata_filter,
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

    def retrieve_with_scores(
        self, query: str, top_k: int = 5
    ) -> list[dict]:
        """检索并返回格式化结果（带分数）"""
        docs = self.retrieve(query, top_k)
        return [
            {
                "content": doc.page_content,
                "score": doc.metadata.get("score", 0),
                "metadata": doc.metadata,
            }
            for doc in docs
        ]

    def as_retriever(self, top_k: int = 5):
        """转为 LangChain Retriever（兼容 LCEL）"""
        def _retrieve(query: str):
            return self.retrieve(query, top_k)
        return RunnableLambda(_retrieve)

    def count(self) -> int:
        return self._chroma.count(KNOWLEDGE_COLLECTION)

    def delete(self, doc_id: str) -> None:
        self._chroma.delete(KNOWLEDGE_COLLECTION, [doc_id])

    def list_documents(self, limit: int = 100, offset: int = 0) -> list[dict]:
        raw = self._chroma.get_all(KNOWLEDGE_COLLECTION, limit=limit, offset=offset)
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
            })
        return docs

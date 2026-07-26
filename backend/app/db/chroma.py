"""
ChromaDB 客户端封装
提供向量存储的连接管理和 CRUD 操作

支持自动降级：
1. 优先尝试 HTTP 客户端（连接 Docker 中的 ChromaDB）
2. 失败时回退到 PersistentClient（本地嵌入式模式）
"""
import os
import concurrent.futures
import chromadb
from chromadb.config import Settings
from typing import Optional

from app.core.config import config

CHROMA_CONNECT_TIMEOUT = float(os.getenv("CHROMA_CONNECT_TIMEOUT", "5"))


def _connect_http_client():
    client = chromadb.HttpClient(
        host=config.chroma.host,
        port=config.chroma.port,
        settings=Settings(anonymized_telemetry=False),
    )
    client.heartbeat()
    return client


class ChromaClient:
    """ChromaDB 客户端单例"""

    _instance: Optional["ChromaClient"] = None

    def __init__(self):
        self._collections: dict[str, chromadb.Collection] = {}

        # 尝试 HTTP 客户端（带超时），失败则回退到 PersistentClient
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_connect_http_client)
                self._client = future.result(timeout=CHROMA_CONNECT_TIMEOUT)
            print(f"[ChromaDB] Connected via HTTP to {config.chroma.host}:{config.chroma.port}")
            self._remote = True
        except Exception as e:
            # 回退到本地持久化模式
            persist_path = os.path.abspath(config.chroma.persist_dir)
            os.makedirs(persist_path, exist_ok=True)
            print(f"[ChromaDB] HTTP client unavailable ({e}), falling back to PersistentClient at {persist_path}")
            self._client = chromadb.PersistentClient(
                path=persist_path,
                settings=Settings(anonymized_telemetry=False),
            )
            self._remote = False

    @property
    def is_remote(self) -> bool:
        """是否使用远程 ChromaDB（服务端负责 embedding，无需本地下载模型）"""
        return getattr(self, "_remote", False)

    @classmethod
    def get_instance(cls) -> "ChromaClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_or_create_collection(
        self, name: str, embedding_dim: int = 1536
    ) -> chromadb.Collection:
        """获取或创建集合"""
        if name not in self._collections:
            try:
                self._collections[name] = self._client.get_collection(name)
            except Exception:
                self._collections[name] = self._client.create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"},
                )
        return self._collections[name]

    def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        metadatas: Optional[list[dict]] = None,
        embeddings: Optional[list[list[float]]] = None,
    ) -> None:
        """向集合添加文档"""
        collection = self.get_or_create_collection(collection_name)
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(
        self,
        collection_name: str,
        query_texts: list[str],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        """查询相似文档"""
        collection = self.get_or_create_collection(collection_name)
        return collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where,
        )

    def delete(self, collection_name: str, ids: list[str]) -> None:
        """删除文档"""
        collection = self.get_or_create_collection(collection_name)
        collection.delete(ids=ids)

    def count(self, collection_name: str) -> int:
        """获取集合文档数量"""
        collection = self.get_or_create_collection(collection_name)
        return collection.count()

    def get_all(
        self,
        collection_name: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """获取集合中的文档列表"""
        collection = self.get_or_create_collection(collection_name)
        return collection.get(limit=limit, offset=offset, include=["documents", "metadatas"])

    def list_collections(self) -> list[str]:
        """列出所有集合"""
        return [c.name for c in self._client.list_collections()]


def get_chroma_client() -> ChromaClient:
    return ChromaClient.get_instance()

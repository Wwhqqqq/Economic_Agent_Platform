from __future__ import annotations

import os
import shutil

from app.storage.base import StorageBackend

OBJECT_ROOT = os.path.join("data", "objects")


class LocalStorage(StorageBackend):
    """Local filesystem storage — S3-compatible key layout."""

    def __init__(self, root: str | None = None):
        self.root = os.path.abspath(root or OBJECT_ROOT)
        os.makedirs(self.root, exist_ok=True)

    def _full_path(self, key: str) -> str:
        safe = key.replace("\\", "/").lstrip("/")
        path = os.path.join(self.root, *safe.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def save_bytes(self, key: str, data: bytes) -> str:
        path = self._full_path(key)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def save_text(self, key: str, text: str, encoding: str = "utf-8") -> str:
        path = self._full_path(key)
        with open(path, "w", encoding=encoding) as f:
            f.write(text)
        return path

    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        with open(self._full_path(key), "r", encoding=encoding) as f:
            return f.read()

    def read_bytes(self, key: str) -> bytes:
        with open(self._full_path(key), "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        return os.path.isfile(self._full_path(key))

    def delete_prefix(self, prefix: str) -> None:
        path = self._full_path(prefix)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.isfile(path):
            os.remove(path)


def doc_object_prefix(user_id: int, doc_id: str) -> str:
    return f"{user_id}/{doc_id}"


def doc_source_key(user_id: int, doc_id: str, ext: str = "") -> str:
    safe_ext = ext if ext.startswith(".") else f".{ext}" if ext else ""
    return f"{doc_object_prefix(user_id, doc_id)}/source{safe_ext}"


def media_asset_key(user_id: int, asset_id: str, filename: str) -> str:
    safe = os.path.basename(filename or "asset.bin")
    return f"{user_id}/media/{asset_id}/{safe}"


def media_thumb_key(user_id: int, asset_id: str) -> str:
    return f"{user_id}/media/{asset_id}/thumb.png"


def doc_content_key(user_id: int, doc_id: str) -> str:
    return f"{doc_object_prefix(user_id, doc_id)}/content.txt"


def doc_ndm_key(user_id: int, doc_id: str) -> str:
    return f"{doc_object_prefix(user_id, doc_id)}/ndm.json"


_storage: LocalStorage | None = None


def get_storage() -> LocalStorage:
    global _storage
    if _storage is None:
        _storage = LocalStorage()
    return _storage

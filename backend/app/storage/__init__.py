from app.storage.base import StorageBackend
from app.storage.local import LocalStorage, get_storage, doc_content_key, doc_ndm_key, doc_object_prefix, doc_source_key, media_asset_key, media_thumb_key

__all__ = [
    "StorageBackend",
    "LocalStorage",
    "get_storage",
    "doc_content_key",
    "doc_ndm_key",
    "doc_object_prefix",
    "doc_source_key",
    "media_asset_key",
    "media_thumb_key",
]
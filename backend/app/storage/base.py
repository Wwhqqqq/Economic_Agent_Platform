from __future__ import annotations

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def save_bytes(self, key: str, data: bytes) -> str:
        """Persist bytes; return URI/path."""

    @abstractmethod
    def save_text(self, key: str, text: str, encoding: str = "utf-8") -> str:
        """Persist text; return URI/path."""

    @abstractmethod
    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        """Read text by key."""

    @abstractmethod
    def read_bytes(self, key: str) -> bytes:
        """Read raw bytes by key."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if object exists."""

    @abstractmethod
    def delete_prefix(self, prefix: str) -> None:
        """Delete all objects under prefix."""

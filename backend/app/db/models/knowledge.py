from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True, index=True
    )
    visibility: Mapped[str] = mapped_column(
        Enum("private", "member", name="knowledge_visibility_enum"),
        nullable=False,
        default="private",
        server_default="private",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    parse_status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "parsing",
            "ready",
            "failed",
            "needs_review",
            name="knowledge_parse_status_enum",
        ),
        nullable=False,
        default="ready",
        server_default="ready",
    )
    parser_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ndm_uri: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text", server_default="text")
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    doc_class: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    table_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

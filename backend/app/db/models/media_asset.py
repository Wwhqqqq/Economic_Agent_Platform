from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    doc_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("knowledge_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="upload")
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    image_class: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ocr_engine: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bbox: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    thumbnail_uri: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    vlm_caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vlm_structured: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vlm_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vlm_engine: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class KnowledgeTable(Base):
    __tablename__ = "knowledge_tables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doc_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    caption: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    cells_json: Mapped[str] = mapped_column(Text, nullable=False)
    markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

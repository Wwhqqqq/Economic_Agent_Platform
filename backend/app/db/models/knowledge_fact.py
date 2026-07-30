from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class KnowledgeFact(Base):
    __tablename__ = "knowledge_facts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    doc_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    metric_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metric_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    value_num: Mapped[Optional[float]] = mapped_column(Numeric(24, 4), nullable=True)
    value_text: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

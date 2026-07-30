from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine, delete, or_, select
from sqlalchemy.orm import Session

from app.core.database import DATABASE_URL
from app.db.models.knowledge_fact import KnowledgeFact
from app.db.models.knowledge_table import KnowledgeTable
from app.ingestion.pdf.metrics import standardize_metric
from app.ingestion.pdf.table_chunker import _parse_number
from app.ingestion.pdf.table_extractor import ExtractedTable

SYNC_DATABASE_URL = DATABASE_URL.replace("+aiomysql", "+pymysql")
_sync_engine = None


def _engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)
    return _sync_engine


@dataclass
class FactRecord:
    company: str | None
    metric_code: str | None
    metric_name: str
    period: str | None
    value_num: float | None
    value_text: str | None
    unit: str | None
    source_page: int | None
    confidence: float
    table_id: str | None = None


class TableStore:
    def insert_tables_sync(
        self,
        tables: list[ExtractedTable],
        *,
        doc_id: str,
        user_id: int,
    ) -> int:
        if not tables:
            return 0
        with Session(_engine()) as session:
            for table in tables:
                session.add(
                    KnowledgeTable(
                        id=table.table_id,
                        doc_id=doc_id,
                        user_id=user_id,
                        page_no=table.page_no,
                        caption=table.caption,
                        cells_json=json.dumps(table.cells, ensure_ascii=False),
                        markdown=table.markdown,
                        quality_json=json.dumps(table.quality, ensure_ascii=False),
                        section_path=table.section_path,
                    )
                )
            session.commit()
        return len(tables)

    def delete_by_doc_sync(self, doc_id: str) -> None:
        with Session(_engine()) as session:
            session.execute(delete(KnowledgeTable).where(KnowledgeTable.doc_id == doc_id))
            session.commit()


class FactStore:
    PERIOD_PATTERN = re.compile(r"(20\d{2}|19\d{2})(?:年|Q[1-4]|-)?")

    def extract_facts_from_table(
        self,
        table: ExtractedTable,
        *,
        doc_id: str,
        user_id: int,
        company: str | None = None,
    ) -> list[FactRecord]:
        facts: list[FactRecord] = []
        if not table.cells or len(table.cells) < 2:
            return facts
        header = table.cells[0]
        periods = []
        for col in header[1:]:
            m = self.PERIOD_PATTERN.search(col or "")
            periods.append(m.group(0) if m else (col or "").strip())

        conf = float(table.quality.get("confidence", 0.7))

        for row in table.cells[1:]:
            if not row or not row[0].strip():
                continue
            metric_name, metric_code = standardize_metric(row[0])
            for i, val in enumerate(row[1:], start=0):
                text = (val or "").strip()
                if not text:
                    continue
                num = _parse_number(text)
                period = periods[i] if i < len(periods) else None
                facts.append(
                    FactRecord(
                        company=company,
                        metric_code=metric_code or None,
                        metric_name=metric_name,
                        period=period,
                        value_num=num,
                        value_text=text,
                        unit="CNY" if num is not None else None,
                        source_page=table.page_no,
                        confidence=conf,
                        table_id=table.table_id,
                    )
                )
        return facts

    def insert_facts_sync(
        self,
        facts: list[FactRecord],
        *,
        doc_id: str,
        user_id: int,
    ) -> int:
        if not facts:
            return 0
        with Session(_engine()) as session:
            for fact in facts:
                session.add(
                    KnowledgeFact(
                        user_id=user_id,
                        doc_id=doc_id,
                        table_id=fact.table_id,
                        company=fact.company,
                        metric_code=fact.metric_code,
                        metric_name=fact.metric_name,
                        period=fact.period,
                        value_num=fact.value_num,
                        value_text=fact.value_text,
                        unit=fact.unit,
                        source_page=fact.source_page,
                        confidence=fact.confidence,
                    )
                )
            session.commit()
        return len(facts)

    def query_facts(
        self,
        *,
        user_id: int,
        metric_name: str | None = None,
        company: str | None = None,
        period: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        with Session(_engine()) as session:
            stmt = select(KnowledgeFact).where(KnowledgeFact.user_id == user_id)
            if metric_name:
                stmt = stmt.where(
                    or_(
                        KnowledgeFact.metric_name.contains(metric_name),
                        KnowledgeFact.metric_code.contains(metric_name),
                    )
                )
            if company:
                stmt = stmt.where(KnowledgeFact.company.contains(company))
            if period:
                stmt = stmt.where(KnowledgeFact.period.contains(period))
            stmt = stmt.order_by(KnowledgeFact.confidence.desc()).limit(limit)
            rows = session.scalars(stmt).all()
            return [
                {
                    "id": row.id,
                    "doc_id": row.doc_id,
                    "table_id": row.table_id,
                    "company": row.company,
                    "metric_code": row.metric_code,
                    "metric_name": row.metric_name,
                    "period": row.period,
                    "value_num": float(row.value_num) if row.value_num is not None else None,
                    "value_text": row.value_text,
                    "unit": row.unit,
                    "source_page": row.source_page,
                    "confidence": row.confidence,
                }
                for row in rows
            ]

    def delete_by_doc_sync(self, doc_id: str) -> None:
        with Session(_engine()) as session:
            session.execute(delete(KnowledgeFact).where(KnowledgeFact.doc_id == doc_id))
            session.commit()


_table_store: TableStore | None = None
_fact_store: FactStore | None = None


def get_table_store() -> TableStore:
    global _table_store
    if _table_store is None:
        _table_store = TableStore()
    return _table_store


def get_fact_store() -> FactStore:
    global _fact_store
    if _fact_store is None:
        _fact_store = FactStore()
    return _fact_store

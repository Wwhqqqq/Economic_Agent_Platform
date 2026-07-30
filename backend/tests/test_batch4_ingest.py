"""Batch 4 acceptance tests."""
from __future__ import annotations

import io
import json
import uuid

import pytest

fitz = pytest.importorskip("fitz")

from app.ingestion.pdf.financial_template import detect_financial_report
from app.ingestion.pdf.metrics import standardize_metric
from app.ingestion.pdf.table_chunker import chunk_table
from app.ingestion.pdf.table_extractor import ExtractedTable, _cells_to_markdown
from app.rag.fact_store import FactStore
from app.rag.query_router import get_query_router
from app.rag.reranker import get_reranker
from langchain_core.documents import Document


def test_table_chunker_summary_and_rows():
    table = ExtractedTable(
        table_id="p1_t1",
        page_no=5,
        caption="资产负债表",
        cells=[
            ["项目", "2024年", "2023年"],
            ["货币资金", "1,234,567", "987,654"],
            ["应收账款", "456,789", "400,000"],
        ],
        markdown=_cells_to_markdown([
            ["项目", "2024年", "2023年"],
            ["货币资金", "1,234,567", "987,654"],
        ]),
        quality={"confidence": 0.9},
        section_path="资产负债表",
    )
    bundle = chunk_table(table, "doc-1")
    assert bundle.summary_chunk.content_type == "table_summary"
    assert len(bundle.row_chunks) >= 1
    assert "货币资金" in bundle.row_chunks[0].text


def test_fact_extraction_from_table():
    table = ExtractedTable(
        table_id="p5_t1",
        page_no=5,
        caption="资产负债表",
        cells=[
            ["项目", "2024年", "2023年"],
            ["货币资金", "1,234,567", "987,654"],
        ],
        markdown="",
        quality={"confidence": 0.88},
    )
    facts = FactStore().extract_facts_from_table(table, doc_id="d1", user_id=1)
    assert len(facts) >= 2
    cash = [f for f in facts if "货币资金" in f.metric_name][0]
    assert cash.value_num == 1234567.0
    assert cash.source_page == 5


def test_query_router_fact_intent():
    plan = get_query_router().analyze("2024年货币资金是多少？")
    assert plan.intent == "fact_lookup"
    assert plan.needs_fact is True


def test_reranker_prefers_table_row():
    docs = [
        Document(page_content="generic paragraph about finance", metadata={"score": 0.5, "content_type": "paragraph"}),
        Document(page_content="cash metric 2024=1,234,567 revenue table", metadata={"score": 0.45, "content_type": "table_row"}),
    ]
    ranked = get_reranker().rerank("cash metric 2024 amount", docs, top_k=2)
    assert ranked[0].metadata.get("content_type") == "table_row"


def test_financial_report_detection():
    text = "本公司2024年度报告 财务报表 资产负债表 利润表 现金流量表"
    assert detect_financial_report(text) is True


def test_standardize_metric():
    name, code = standardize_metric("货币资金")
    assert name == "货币资金"
    assert code == "cash_and_equivalents"

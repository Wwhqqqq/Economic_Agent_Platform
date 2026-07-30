from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass

from app.ingestion.chunker import ChunkRecord, content_hash, estimate_tokens
from app.ingestion.pdf.table_extractor import ExtractedTable

SKIP_ROW_PATTERNS = re.compile(r"^(合计|小计|总计|-+|—+)$", re.I)
NUMERIC_ROW = re.compile(r"[\d,.]+")


def _parse_number(text: str) -> float | None:
    text = (text or "").strip()
    if not text or text in ("-", "—", "N/A"):
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = text.replace(",", "").replace("，", "")
    text = re.sub(r"[^\d.\-]", "", text)
    if not text:
        return None
    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return None


@dataclass
class TableChunkBundle:
    summary_chunk: ChunkRecord
    row_chunks: list[ChunkRecord]


def build_table_summary_chunk(table: ExtractedTable, doc_id: str, *, seq: int = 0) -> ChunkRecord:
    key_rows: list[str] = []
    for row in table.cells[1:8]:
        if not row or not row[0].strip():
            continue
        label = row[0].strip()
        if SKIP_ROW_PATTERNS.match(label):
            continue
        values = " | ".join(v for v in row[1:4] if v.strip())
        if values:
            key_rows.append(f"{label} {values}")
    summary_text = (
        f"[TABLE SUMMARY {table.table_id}] {table.caption or '表格'} (Page {table.page_no})\n"
        f"列：{' | '.join(table.cells[0]) if table.cells else ''}\n"
        f"行数：{len(table.cells)}\n"
        f"关键行：{'；'.join(key_rows[:6])}"
    )
    cid = str(uuid.uuid4())
    return ChunkRecord(
        chunk_id=cid,
        doc_id=doc_id,
        seq=seq,
        text=summary_text,
        token_count=estimate_tokens(summary_text),
        content_type="table_summary",
        section_path=table.section_path or table.caption or f"Page {table.page_no}",
        content_hash=content_hash(summary_text),
        block_ids=[table.table_id],
        page_range=str(table.page_no),
    )


def build_table_row_chunks(table: ExtractedTable, doc_id: str, *, start_seq: int = 0) -> list[ChunkRecord]:
    if not table.cells or len(table.cells) < 2:
        return []
    header = table.cells[0]
    period_cols = header[1:] if len(header) > 1 else []
    row_chunks: list[ChunkRecord] = []
    seq = start_seq
    table_label = table.caption or table.section_path or "表格"

    for row in table.cells[1:]:
        if not row or not row[0].strip():
            continue
        row_key = row[0].strip()
        if SKIP_ROW_PATTERNS.match(row_key):
            continue
        if not NUMERIC_ROW.search(" ".join(row[1:])) and len(row) > 1:
            continue
        parts = [f"[TABLE ROW {table.table_id}] {table_label} | {row_key}"]
        for i, val in enumerate(row[1:], start=0):
            period = period_cols[i] if i < len(period_cols) else f"col{i + 1}"
            if val.strip():
                parts.append(f"{period}={val.strip()}")
        text = " | ".join(parts)
        cid = str(uuid.uuid4())
        row_chunks.append(
            ChunkRecord(
                chunk_id=cid,
                doc_id=doc_id,
                seq=seq,
                text=text,
                token_count=estimate_tokens(text),
                content_type="table_row",
                section_path=table.section_path or table.caption or f"Page {table.page_no}",
                content_hash=content_hash(text),
                block_ids=[table.table_id],
                page_range=str(table.page_no),
            )
        )
        seq += 1
    return row_chunks


def chunk_table(table: ExtractedTable, doc_id: str, *, seq: int = 0) -> TableChunkBundle:
    summary = build_table_summary_chunk(table, doc_id, seq=seq)
    rows = build_table_row_chunks(table, doc_id, start_seq=seq + 1)
    return TableChunkBundle(summary_chunk=summary, row_chunks=rows)


def chunk_all_tables(tables: list[ExtractedTable], doc_id: str) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    seq = 0
    for table in tables:
        bundle = chunk_table(table, doc_id, seq=seq)
        chunks.append(bundle.summary_chunk)
        chunks.extend(bundle.row_chunks)
        seq += 1 + len(bundle.row_chunks)
    return chunks

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field

_pdfplumber = None


def _get_pdfplumber():
    global _pdfplumber
    if _pdfplumber is None:
        import pdfplumber
        _pdfplumber = pdfplumber
    return _pdfplumber


@dataclass
class ExtractedTable:
    table_id: str
    page_no: int
    caption: str
    cells: list[list[str]]
    markdown: str
    bbox: list[float] = field(default_factory=list)
    quality: dict = field(default_factory=dict)
    section_path: str = ""


def _cells_to_markdown(cells: list[list[str]]) -> str:
    if not cells:
        return ""
    rows = [[(c or "").strip() for c in row] for row in cells]
    max_cols = max(len(r) for r in rows)
    normalized = [r + [""] * (max_cols - len(r)) for r in rows]
    if not normalized:
        return ""
    header = normalized[0]
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _cell_fill_rate(cells: list[list[str]]) -> float:
    if not cells:
        return 0.0
    total = sum(len(r) for r in cells)
    filled = sum(1 for r in cells for c in r if (c or "").strip())
    return filled / max(1, total)


def _numeric_ratio(cells: list[list[str]]) -> float:
    numeric = 0
    total = 0
    for row in cells:
        for cell in row:
            text = (cell or "").strip()
            if not text:
                continue
            total += 1
            if re.search(r"[\d,.()%\-]", text):
                numeric += 1
    return numeric / max(1, total)


def extract_tables_from_pdf(pdf_bytes: bytes, *, doc_id: str = "") -> list[ExtractedTable]:
    """Extract tables using pdfplumber; returns structured table records."""
    tables: list[ExtractedTable] = []
    try:
        pdfplumber = _get_pdfplumber()
        import io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_index, page in enumerate(pdf.pages):
                page_no = page_index + 1
                raw_tables = page.extract_tables() or []
                for ti, raw in enumerate(raw_tables):
                    if not raw or len(raw) < 2:
                        continue
                    cells = [[str(c or "").strip() for c in row] for row in raw]
                    fill = _cell_fill_rate(cells)
                    if fill < 0.35:
                        continue
                    table_id = f"p{page_no}_t{ti + 1}"
                    caption = ""
                    if cells[0] and any(cells[0]):
                        caption = " / ".join(c for c in cells[0] if c)[:200]
                    quality = {
                        "detection_method": "pdfplumber",
                        "cell_fill_rate": round(fill, 3),
                        "numeric_cell_ratio": round(_numeric_ratio(cells), 3),
                        "confidence": round(min(0.99, 0.5 + fill * 0.4), 3),
                    }
                    tables.append(
                        ExtractedTable(
                            table_id=table_id,
                            page_no=page_no,
                            caption=caption,
                            cells=cells,
                            markdown=_cells_to_markdown(cells),
                            bbox=[float(x) for x in (page.bbox or [0, 0, 0, 0])],
                            quality=quality,
                        )
                    )
    except Exception as exc:
        print(f"[table_extractor] pdfplumber failed: {exc}")
    return tables


def extract_tables_from_text_blocks(pages, *, doc_id: str = "") -> list[ExtractedTable]:
    """Fallback: detect tabular blocks from aligned text columns."""
    tables: list[ExtractedTable] = []
    for page in pages:
        tab_blocks = [
            b for b in page.blocks
            if b.role == "body" and (b.text.count("\t") >= 2 or b.text.count("|") >= 2)
        ]
        for bi, block in enumerate(tab_blocks):
            lines = [ln.strip() for ln in block.text.splitlines() if ln.strip()]
            if len(lines) < 2:
                continue
            cells = []
            for line in lines:
                if "|" in line:
                    cells.append([c.strip() for c in line.split("|") if c.strip()])
                elif "\t" in line:
                    cells.append([c.strip() for c in line.split("\t")])
                else:
                    cells.append(re.split(r"\s{2,}", line))
            if len(cells) < 2:
                continue
            table_id = f"p{page.page_no}_tb{bi + 1}"
            tables.append(
                ExtractedTable(
                    table_id=table_id,
                    page_no=page.page_no,
                    caption=cells[0][0] if cells and cells[0] else "",
                    cells=cells,
                    markdown=_cells_to_markdown(cells),
                    bbox=list(block.bbox),
                    quality={
                        "detection_method": "text_align",
                        "cell_fill_rate": round(_cell_fill_rate(cells), 3),
                        "confidence": 0.55,
                    },
                )
            )
    return tables

from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.pdf.preprocessor import PdfPage, TextBlock


@dataclass
class PdfClassification:
    doc_class: str
    confidence: float
    avg_chars_per_page: float
    page_count: int
    signals: dict


SCANNED_CHARS_THRESHOLD = 80
TABLE_HEAVY_LINE_THRESHOLD = 120


def classify_pdf_pages(pages: list[PdfPage]) -> PdfClassification:
    page_count = len(pages)
    if page_count == 0:
        return PdfClassification(
            doc_class="scanned",
            confidence=0.99,
            avg_chars_per_page=0,
            page_count=0,
            signals={"has_text_layer": False},
        )

    char_counts = [sum(len(b.text) for b in p.blocks) for p in pages]
    avg_chars = sum(char_counts) / page_count
    has_text_layer = avg_chars >= 20

    line_blocks = sum(
        1 for p in pages for b in p.blocks if b.text.count("|") >= 2 or b.text.count("\t") >= 2
    )

    signals = {
        "has_text_layer": has_text_layer,
        "avg_chars_per_page": round(avg_chars, 1),
        "line_block_count": line_blocks,
    }

    if not has_text_layer or avg_chars < SCANNED_CHARS_THRESHOLD:
        return PdfClassification(
            doc_class="scanned",
            confidence=0.92 if avg_chars < 20 else 0.78,
            avg_chars_per_page=avg_chars,
            page_count=page_count,
            signals=signals,
        )

    if line_blocks >= TABLE_HEAVY_LINE_THRESHOLD:
        return PdfClassification(
            doc_class="table_heavy",
            confidence=0.75,
            avg_chars_per_page=avg_chars,
            page_count=page_count,
            signals=signals,
        )

    return PdfClassification(
        doc_class="native_text",
        confidence=0.9,
        avg_chars_per_page=avg_chars,
        page_count=page_count,
        signals=signals,
    )

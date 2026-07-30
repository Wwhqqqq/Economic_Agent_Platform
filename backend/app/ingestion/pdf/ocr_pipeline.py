from __future__ import annotations

import io
from dataclasses import dataclass, field

import fitz

from app.ingestion.media.ocr import ocr_image
from app.ingestion.pdf.preprocessor import PdfPage, TextBlock, mark_header_footer_blocks


@dataclass
class OcrPageResult:
    page_no: int
    text: str
    quality: float
    engine: str


@dataclass
class PdfOcrResult:
    pages: list[PdfPage] = field(default_factory=list)
    plain_text: str = ""
    avg_quality: float = 0.0
    page_count: int = 0
    engines: list[str] = field(default_factory=list)


def _render_page_png(page, dpi: int = 200) -> bytes:
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def ocr_pdf_pages(pdf_bytes: bytes, *, dpi: int = 200, max_pages: int = 128) -> PdfOcrResult:
    """Render scanned PDF pages and OCR each page."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    ocr_pages: list[OcrPageResult] = []
    pdf_pages: list[PdfPage] = []
    try:
        page_total = min(len(doc), max_pages)
        for page_index in range(page_total):
            page = doc.load_page(page_index)
            page_no = page_index + 1
            rect = page.rect
            png_bytes = _render_page_png(page, dpi=dpi)
            ocr = ocr_image(png_bytes)
            text = (ocr.text or "").strip()
            ocr_pages.append(
                OcrPageResult(
                    page_no=page_no,
                    text=text,
                    quality=ocr.quality,
                    engine=ocr.engine,
                )
            )
            blocks: list[TextBlock] = []
            if text:
                blocks.append(
                    TextBlock(
                        block_id=f"ocr_p{page_no}_b0",
                        text=text,
                        page_no=page_no,
                        bbox=[0, 0, float(rect.width), float(rect.height)],
                        role="body",
                    )
                )
            pdf_pages.append(
                PdfPage(
                    page_no=page_no,
                    width=float(rect.width),
                    height=float(rect.height),
                    blocks=blocks,
                )
            )
    finally:
        doc.close()

    qualities = [p.quality for p in ocr_pages if p.text]
    avg_quality = sum(qualities) / len(qualities) if qualities else 0.0
    engines = list({p.engine for p in ocr_pages if p.engine})

    pdf_pages = mark_header_footer_blocks(pdf_pages)
    parts: list[str] = []
    for page in pdf_pages:
        body = [b.text for b in page.blocks if b.role == "body" and b.text.strip()]
        if not body:
            continue
        parts.append(f"[Page {page.page_no}]")
        parts.extend(body)
        parts.append("")
    plain_text = "\n".join(parts).strip()

    return PdfOcrResult(
        pages=pdf_pages,
        plain_text=plain_text,
        avg_quality=round(avg_quality, 3),
        page_count=len(ocr_pages),
        engines=engines,
    )

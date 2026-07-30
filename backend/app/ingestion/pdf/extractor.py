from __future__ import annotations

import fitz

from app.ingestion.pdf.preprocessor import PdfPage, TextBlock


MIN_FIGURE_AREA = 80 * 80


class FigureRegion:
    __slots__ = ("figure_id", "page_no", "bbox", "image_bytes", "caption_hint")

    def __init__(
        self,
        figure_id: str,
        page_no: int,
        bbox: list[float],
        image_bytes: bytes,
        caption_hint: str = "",
    ):
        self.figure_id = figure_id
        self.page_no = page_no
        self.bbox = bbox
        self.image_bytes = image_bytes
        self.caption_hint = caption_hint


def _nearby_caption(page: fitz.Page, rect: fitz.Rect) -> str:
    blocks = page.get_text("blocks") or []
    hints: list[str] = []
    for block in blocks:
        if len(block) < 5:
            continue
        x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
        cleaned = (text or "").strip()
        if not cleaned or len(cleaned) > 120:
            continue
        if y0 >= rect.y1 and y0 - rect.y1 < 40:
            hints.append(cleaned)
        elif y1 <= rect.y0 and rect.y0 - y1 < 40:
            hints.append(cleaned)
    return " ".join(hints[:2])


def extract_pdf_figures(pdf_bytes: bytes, *, min_area: int = MIN_FIGURE_AREA) -> list[FigureRegion]:
    """Extract embedded images from PDF pages as figure regions."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    figures: list[FigureRegion] = []
    seen: set[str] = set()
    try:
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            page_no = page_index + 1
            for img in page.get_images(full=True):
                xref = img[0]
                try:
                    rects = page.get_image_rects(xref)
                except Exception:
                    continue
                for ri, rect in enumerate(rects):
                    area = rect.width * rect.height
                    if area < min_area:
                        continue
                    key = f"{page_no}:{xref}:{ri}"
                    if key in seen:
                        continue
                    seen.add(key)
                    try:
                        pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(2, 2))
                        image_bytes = pix.tobytes("png")
                    except Exception:
                        continue
                    caption_hint = _nearby_caption(page, rect)
                    figures.append(
                        FigureRegion(
                            figure_id=f"p{page_no}_fig{len(figures) + 1}",
                            page_no=page_no,
                            bbox=[float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)],
                            image_bytes=image_bytes,
                            caption_hint=caption_hint,
                        )
                    )
    finally:
        doc.close()
    return figures


def extract_pdf_pages(pdf_bytes: bytes) -> list[PdfPage]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PdfPage] = []
    try:
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            page_no = page_index + 1
            rect = page.rect
            pdf_page = PdfPage(
                page_no=page_no,
                width=float(rect.width),
                height=float(rect.height),
            )
            blocks = page.get_text("blocks") or []
            for bi, block in enumerate(blocks):
                if len(block) < 5:
                    continue
                x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
                cleaned = (text or "").strip()
                if not cleaned:
                    continue
                pdf_page.blocks.append(
                    TextBlock(
                        block_id=f"p{page_no}_b{bi}",
                        text=cleaned,
                        page_no=page_no,
                        bbox=[float(x0), float(y0), float(x1), float(y1)],
                    )
                )
            pages.append(pdf_page)
    finally:
        doc.close()
    return pages

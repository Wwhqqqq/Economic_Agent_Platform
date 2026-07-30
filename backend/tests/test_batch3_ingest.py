"""Batch 3 acceptance tests: PDF text layer + image OCR pipeline."""
from __future__ import annotations

import io
import sys
from unittest.mock import patch

import pytest

fitz = pytest.importorskip("fitz")

from app.ingestion.pdf.classifier import classify_pdf_pages
from app.ingestion.pdf.extractor import extract_pdf_pages
from app.ingestion.pdf.pipeline import prepare_pdf_ingest
from app.ingestion.pdf.preprocessor import mark_header_footer_blocks, pages_to_plain_text
from app.ingestion.media.ocr import OcrResult
from app.ingestion.media.service import prepare_media_ingest


def _make_pdf_with_header(*, pages: int = 3) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 20), "CONFIDENTIAL HEADER", fontsize=8)
        page.insert_text((72, 700), f"Page {i + 1}", fontsize=8)
        page.insert_text(
            (72, 100),
            f"Section {i + 1}: financial analysis revenue growth quarter report.",
            fontsize=11,
        )
    data = doc.tobytes()
    doc.close()
    return data


def _make_blank_pdf(*, pages: int = 2) -> bytes:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def test_pdf_native_classified_and_header_removed():
    pdf_bytes = _make_pdf_with_header()
    pages = extract_pdf_pages(pdf_bytes)
    cls = classify_pdf_pages(pages)
    assert cls.doc_class == "native_text"
    pages = mark_header_footer_blocks(pages)
    text = pages_to_plain_text(pages)
    assert "CONFIDENTIAL HEADER" not in text
    assert "financial analysis" in text


def test_pdf_native_ingest_ready_with_chunks():
    pdf_bytes = _make_pdf_with_header()
    result = prepare_pdf_ingest(pdf_bytes, "test-pdf-doc", user_id=1, filename="report.pdf")
    assert result.parse_status == "ready"
    assert len(result.chunks) >= 1
    assert result.page_count == 3


def test_scanned_pdf_needs_review_no_chunks():
    pdf_bytes = _make_blank_pdf()
    result = prepare_pdf_ingest(pdf_bytes, "scan-doc", user_id=1, filename="scan.pdf")
    assert result.parse_status == "needs_review"
    assert result.chunks == []


def test_image_ocr_ingest_with_mock():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        pytest.skip("Pillow not installed")

    img = Image.new("RGB", (400, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), "Revenue Q3 2025", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    fake_ocr = OcrResult(text="Revenue Q3 2025 exceeded expectations", quality=0.88, engine="test")

    with patch("app.ingestion.media.service.ocr_image", return_value=fake_ocr):
        result = prepare_media_ingest(image_bytes, "img-doc", user_id=1, filename="chart.png")

    assert result.parse_status == "ready"
    assert len(result.chunks) >= 1
    assert "Revenue" in result.plain_text
    assert result.media_asset_id


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

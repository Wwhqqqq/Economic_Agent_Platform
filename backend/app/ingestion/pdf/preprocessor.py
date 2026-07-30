from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class TextBlock:
    block_id: str
    text: str
    page_no: int
    bbox: list[float]
    role: str = "body"


@dataclass
class PdfPage:
    page_no: int
    width: float
    height: float
    blocks: list[TextBlock] = field(default_factory=list)


@dataclass
class PdfClassification:
    doc_class: str
    confidence: float
    avg_chars_per_page: float
    page_count: int
    signals: dict = field(default_factory=dict)


PAGE_NUM_PATTERN = re.compile(
    r"^(第\s*\d+\s*页|Page\s+\d+\s*(of\s+\d+)?|-\s*\d+\s*-|\d+\s*/\s*\d+)$",
    re.I,
)


def _normalize_line(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def detect_repeated_margin_blocks(pages: list[PdfPage], *, coverage: float = 0.7) -> set[str]:
    """Cross-page repeated header/footer lines (normalized text)."""
    if len(pages) < 2:
        return set()

    top_lines: dict[str, int] = {}
    bottom_lines: dict[str, int] = {}
    page_total = len(pages)

    for page in pages:
        if not page.blocks:
            continue
        h = page.height or 800
        tops = set()
        bots = set()
        for block in page.blocks:
            y0 = block.bbox[1] if len(block.bbox) >= 2 else 0
            y1 = block.bbox[3] if len(block.bbox) >= 4 else y0
            norm = _normalize_line(block.text)
            if not norm or len(norm) < 2:
                continue
            if PAGE_NUM_PATTERN.match(norm):
                tops.add(norm)
                bots.add(norm)
                continue
            if y1 <= h * 0.12:
                tops.add(norm)
            elif y0 >= h * 0.88:
                bots.add(norm)
        for line in tops:
            top_lines[line] = top_lines.get(line, 0) + 1
        for line in bots:
            bottom_lines[line] = bottom_lines.get(line, 0) + 1

    repeated: set[str] = set()
    threshold = max(2, int(page_total * coverage))
    for line, count in {**top_lines, **bottom_lines}.items():
        if count >= threshold:
            repeated.add(line)
    return repeated


def mark_header_footer_blocks(pages: list[PdfPage]) -> list[PdfPage]:
    repeated = detect_repeated_margin_blocks(pages)
    for page in pages:
        h = page.height or 800
        for block in page.blocks:
            norm = _normalize_line(block.text)
            if not norm:
                continue
            if norm in repeated:
                block.role = "header_footer"
                continue
            if PAGE_NUM_PATTERN.match(norm):
                block.role = "page_number"
                continue
            y0 = block.bbox[1] if len(block.bbox) >= 2 else 0
            y1 = block.bbox[3] if len(block.bbox) >= 4 else y0
            if y1 <= h * 0.12 or y0 >= h * 0.88:
                if any(SequenceMatcher(None, norm, rep).ratio() >= 0.9 for rep in repeated):
                    block.role = "header_footer"
    return pages


def normalize_block_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def pages_to_plain_text(pages: list[PdfPage], *, include_page_markers: bool = True) -> str:
    parts: list[str] = []
    for page in pages:
        body_blocks = [b for b in page.blocks if b.role == "body" and b.text.strip()]
        if not body_blocks:
            continue
        if include_page_markers:
            parts.append(f"[Page {page.page_no}]")
        for block in body_blocks:
            parts.append(normalize_block_text(block.text))
        parts.append("")
    return "\n".join(parts).strip()

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ImageClassification:
    image_class: str
    confidence: float


def classify_image(*, width: int, height: int, ocr_text: str, ocr_quality: float) -> ImageClassification:
    text_len = len(ocr_text.strip())
    if text_len >= 40 and ocr_quality >= 0.5:
        return ImageClassification("document_scan", 0.85)
    if text_len >= 10:
        return ImageClassification("document_scan", 0.65)
    aspect = width / max(height, 1)
    if 0.8 <= aspect <= 1.25 and text_len < 10:
        return ImageClassification("photo", 0.6)
    return ImageClassification("unknown", 0.4)

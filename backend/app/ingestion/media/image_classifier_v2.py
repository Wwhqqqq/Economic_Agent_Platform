from __future__ import annotations

import re
from dataclasses import dataclass

from app.ingestion.media.classifier import ImageClassification, classify_image as classify_v1


@dataclass
class ImageClassResult:
    image_class: str
    confidence: float
    skip_index: bool = False
    recommended_pipeline: list[str] | None = None


DECORATIVE_MAX_AREA = 120 * 120
CHART_ASPECT_RANGE = (1.2, 3.5)


def classify_image_v2(
    *,
    width: int,
    height: int,
    ocr_text: str,
    ocr_quality: float,
    caption_hint: str = "",
) -> ImageClassResult:
    area = max(width, 1) * max(height, 1)
    text = (ocr_text or "").strip()
    text_len = len(text)
    aspect = width / max(height, 1)

    hint = (caption_hint or "").lower()
    if any(k in hint for k in ("图", "figure", "chart", "图表", "柱状", "折线", "饼图")):
        return ImageClassResult("chart", 0.82, skip_index=False, recommended_pipeline=["ocr", "vlm_chart"])

    if area < DECORATIVE_MAX_AREA and text_len < 5:
        return ImageClassResult("decorative", 0.9, skip_index=True, recommended_pipeline=[])

    if text_len >= 80 and ocr_quality >= 0.45:
        if re.search(r"(表|table|\||\t)", text, re.I):
            return ImageClassResult("document_scan", 0.8, recommended_pipeline=["ocr"])
        return ImageClassResult("screenshot", 0.75, recommended_pipeline=["ocr"])

    chart_keywords = ("柱状", "折线", "饼图", "营收", "季度", "Q1", "Q2", "Q3", "Q4", "亿元", "万元", "%")
    if any(k in text for k in chart_keywords) or (CHART_ASPECT_RANGE[0] <= aspect <= CHART_ASPECT_RANGE[1] and text_len < 40):
        return ImageClassResult("chart", 0.72, recommended_pipeline=["ocr", "vlm_chart"])

    if text_len < 15 and 0.7 <= aspect <= 1.4:
        return ImageClassResult("photo", 0.65, recommended_pipeline=["vlm_caption", "ocr"])

    if "流程" in text or "架构" in text or "diagram" in hint:
        return ImageClassResult("diagram", 0.7, recommended_pipeline=["vlm_caption"])

    if "logo" in hint or "icon" in hint:
        return ImageClassResult("icon_logo", 0.7, skip_index=True, recommended_pipeline=[])

    v1 = classify_v1(width=width, height=height, ocr_text=text, ocr_quality=ocr_quality)
    return ImageClassResult(
        v1.image_class if v1.image_class != "unknown" else "photo",
        v1.confidence,
        skip_index=False,
        recommended_pipeline=["ocr"],
    )

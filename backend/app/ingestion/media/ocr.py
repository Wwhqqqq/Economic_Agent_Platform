from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional

_ocr_engine = None
_ocr_engine_failed = False


@dataclass
class OcrResult:
    text: str
    quality: float
    engine: str


def _ocr_paddle(image_bytes: bytes) -> Optional[OcrResult]:
    global _ocr_engine, _ocr_engine_failed
    if _ocr_engine_failed:
        return None
    try:
        if _ocr_engine is None:
            from paddleocr import PaddleOCR
            _ocr_engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        from PIL import Image
        import numpy as np

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        raw = _ocr_engine.ocr(arr, cls=True)
        lines: list[str] = []
        confidences: list[float] = []
        for page in raw or []:
            for line in page or []:
                if not line or len(line) < 2:
                    continue
                text_part = line[1][0]
                conf = float(line[1][1])
                if text_part.strip():
                    lines.append(text_part.strip())
                    confidences.append(conf)
        if not lines:
            return OcrResult(text="", quality=0.0, engine="paddleocr")
        avg_conf = sum(confidences) / len(confidences)
        return OcrResult(text="\n".join(lines), quality=round(avg_conf, 3), engine="paddleocr")
    except Exception as exc:
        print(f"[OCR] PaddleOCR unavailable: {exc}")
        _ocr_engine_failed = True
        return None


def _ocr_tesseract(image_bytes: bytes) -> Optional[OcrResult]:
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        text = (text or "").strip()
        quality = min(1.0, len(text) / 200) if text else 0.0
        return OcrResult(text=text, quality=round(quality, 3), engine="tesseract")
    except Exception as exc:
        print(f"[OCR] Tesseract unavailable: {exc}")
        return None


def ocr_image(image_bytes: bytes) -> OcrResult:
    """Run OCR on image bytes; graceful fallback chain."""
    for fn in (_ocr_paddle, _ocr_tesseract):
        result = fn(image_bytes)
        if result and result.text.strip():
            return result
    return OcrResult(text="", quality=0.0, engine="none")

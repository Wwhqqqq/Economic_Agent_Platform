from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

CHART_SCHEMA_KEYS = {"chart_type", "title", "x_axis", "y_axis", "series", "trends", "key_figures"}


@dataclass
class VlmResult:
    caption: str = ""
    structured: dict = field(default_factory=dict)
    quality: float = 0.0
    engine: str = "none"


def content_hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_chart_json(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    cleaned = {k: data.get(k) for k in CHART_SCHEMA_KEYS if k in data}
    figures = cleaned.get("key_figures") or []
    if isinstance(figures, list):
        valid_figs = []
        for fig in figures:
            if not isinstance(fig, dict):
                continue
            label = str(fig.get("label") or "").strip()
            if not label:
                continue
            valid_figs.append({
                "label": label,
                "value": fig.get("value"),
                "unit": fig.get("unit"),
            })
        cleaned["key_figures"] = valid_figs
    return cleaned


def _heuristic_chart_from_ocr(ocr_text: str) -> VlmResult:
    text = (ocr_text or "").strip()
    if not text:
        return VlmResult(engine="heuristic")
    trends: list[str] = []
    if "上升" in text or "增长" in text:
        trends.append("整体呈上升趋势")
    if "下降" in text or "下滑" in text:
        trends.append("整体呈下降趋势")
    figures: list[dict] = []
    for m in re.finditer(r"([^\d\n]{2,20}?)[\s:：]*([\d,.]+)\s*(亿元|万元|%|元)?", text):
        label, val, unit = m.group(1).strip(), m.group(2), m.group(3) or ""
        if len(label) > 18:
            continue
        figures.append({"label": label, "value": val, "unit": unit})
    structured = _validate_chart_json({
        "chart_type": "bar" if "柱" in text else "unknown",
        "title": "",
        "trends": trends,
        "key_figures": figures[:8],
    })
    caption = f"图表内容（OCR 推断）：{text[:300]}"
    if trends:
        caption += "；" + "；".join(trends)
    quality = min(0.85, 0.35 + len(figures) * 0.08 + (0.2 if trends else 0))
    return VlmResult(caption=caption, structured=structured, quality=round(quality, 3), engine="heuristic")


def _vision_llm_describe(image_bytes: bytes, *, image_class: str, ocr_text: str = "") -> VlmResult | None:
    try:
        from app.llm.factory import LLMFactory
        from app.llm.providers import pick_vision_provider
        from app.llm.vision import build_image_data_url, build_vision_human_message
        from langchain_core.messages import HumanMessage, SystemMessage

        provider = pick_vision_provider()
        if not provider:
            return None

        llm = LLMFactory.create(provider)
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = build_image_data_url(b64, mime="image/png")
        prompt = (
            "分析这张图片。若是图表，输出 JSON："
            '{"chart_type":"","title":"","x_axis":"","y_axis":"","series":[],"trends":[],"key_figures":[{"label":"","value":"","unit":""}]}'
            "数值不确定填 null，勿编造。"
        )
        if ocr_text:
            prompt += f"\n\nOCR 参考：{ocr_text[:500]}"
        msg = build_vision_human_message(prompt, data_url)
        response = llm.invoke([SystemMessage(content="你是图表与图像分析助手，只输出 JSON 或简洁描述。"), msg])
        raw = response.content if isinstance(response.content, str) else str(response.content)
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if json_match:
            structured = _validate_chart_json(json.loads(json_match.group()))
            caption = structured.get("title") or raw[:400]
            conf = 0.75 if structured.get("key_figures") else 0.55
            return VlmResult(caption=caption, structured=structured, quality=conf, engine=f"vision:{provider}")
        return VlmResult(caption=raw[:600], structured={}, quality=0.6, engine=f"vision:{provider}")
    except Exception as exc:
        print(f"[VLM] vision LLM unavailable: {exc}")
        return None


def describe_image(
    image_bytes: bytes,
    *,
    image_class: str,
    ocr_text: str = "",
) -> VlmResult:
    if image_class in ("decorative", "icon_logo"):
        return VlmResult(engine="skipped")

    if image_class in ("chart", "diagram", "photo"):
        vision = _vision_llm_describe(image_bytes, image_class=image_class, ocr_text=ocr_text)
        if vision and (vision.caption or vision.structured):
            return vision

    if image_class == "chart" or "chart" in image_class:
        return _heuristic_chart_from_ocr(ocr_text)

    if ocr_text.strip():
        return VlmResult(
            caption=f"图片内容：{ocr_text.strip()[:400]}",
            structured={},
            quality=0.5,
            engine="ocr_caption",
        )
    return VlmResult(engine="none")


def structured_to_facts(
    structured: dict,
    *,
    doc_id: str,
    asset_id: str,
    page_no: int | None,
    min_confidence: float = 0.7,
) -> list:
    from app.rag.fact_store import FactRecord

    facts: list[FactRecord] = []
    if not structured:
        return facts
    for fig in structured.get("key_figures") or []:
        if not isinstance(fig, dict):
            continue
        label = str(fig.get("label") or "").strip()
        val = fig.get("value")
        if not label or val is None or val == "null":
            continue
        num = None
        text_val = str(val)
        try:
            num = float(str(val).replace(",", ""))
        except ValueError:
            pass
        facts.append(
            FactRecord(
                company=None,
                metric_code=label[:64],
                metric_name=label,
                period=None,
                value_num=num,
                value_text=text_val,
                unit=str(fig.get("unit") or ""),
                source_page=page_no,
                confidence=min_confidence,
                table_id=asset_id,
            )
        )
    return facts

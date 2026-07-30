from __future__ import annotations

from langchain_core.messages import HumanMessage


def build_image_data_url(b64_data: str, *, mime: str = "image/png") -> str:
    if b64_data.startswith("data:"):
        return b64_data
    return f"data:{mime};base64,{b64_data}"


def build_vision_human_message(text: str, image_url: str) -> HumanMessage:
    return HumanMessage(
        content=[
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
    )


def build_multimodal_human_message(
    text: str,
    attachments: list[dict],
    *,
    fallback_text: str = "",
) -> HumanMessage:
    """Build HumanMessage with text + image URLs for vision models."""
    parts: list[dict] = []
    body = text.strip() or "请分析附件图片。"
    if fallback_text:
        body = f"{body}\n\n[图片解析摘要]\n{fallback_text}"
    parts.append({"type": "text", "text": body})
    for att in attachments[:4]:
        url = att.get("url") or att.get("data_url")
        if url:
            parts.append({"type": "image_url", "image_url": {"url": url}})
    return HumanMessage(content=parts)


def attachments_fallback_context(attachments: list[dict]) -> str:
    lines: list[str] = []
    for i, att in enumerate(attachments, start=1):
        ocr = att.get("ocr_text") or ""
        caption = att.get("vlm_caption") or att.get("caption") or ""
        if ocr or caption:
            lines.append(f"### 附件 {i}\nOCR: {ocr[:400]}\n描述: {caption[:400]}")
    return "\n\n".join(lines)

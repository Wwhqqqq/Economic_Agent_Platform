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
    body = text.strip() or "请分析附件。"
    if fallback_text:
        body = f"{body}\n\n[附件摘要]\n{fallback_text}"
    parts.append({"type": "text", "text": body})
    for att in attachments[:4]:
        kind = att.get("kind") or ("file" if att.get("file_path") else "image")
        if kind == "file":
            continue
        url = att.get("url") or att.get("data_url")
        if url:
            parts.append({"type": "image_url", "image_url": {"url": url}})
    return HumanMessage(content=parts)


def attachments_fallback_context(attachments: list[dict]) -> str:
    lines: list[str] = []
    for i, att in enumerate(attachments, start=1):
        kind = att.get("kind") or ("file" if att.get("file_path") else "image")
        if kind == "file":
            name = att.get("filename") or att.get("file_path") or f"file-{i}"
            preview = (att.get("text_preview") or "").strip()
            block = f"### 附件 {i}: {name}"
            if preview:
                block += f"\n{preview[:2000]}"
            file_path = att.get("file_path") or att.get("filename")
            if file_path:
                block += f"\n（可用 file_reader 读取：`{file_path}`）"
            lines.append(block)
            continue
        ocr = att.get("ocr_text") or ""
        caption = att.get("vlm_caption") or att.get("caption") or ""
        name = att.get("filename") or f"image-{i}"
        if ocr or caption:
            lines.append(f"### 附件 {i}: {name}\nOCR: {ocr[:800]}\n描述: {caption[:400]}")
        else:
            lines.append(
                f"### 附件 {i}: {name}\n（图片已上传，当前模型无法直接识图；"
                "未能提取到文字内容。请配置支持视觉的模型如 OpenAI/Claude，或上传含文字的图片。）"
            )
    return "\n\n".join(lines)

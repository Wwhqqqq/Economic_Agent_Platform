"""Resolve chat attachments from asset_id to full metadata for the agent."""
from __future__ import annotations

import base64
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.media_asset import MediaAsset
from app.ingestion.media.ocr import ocr_image_fast


async def resolve_chat_attachments(
    db: AsyncSession,
    user_id: int,
    attachments: list[dict],
) -> list[dict]:
    if not attachments or not user_id:
        return attachments

    resolved: list[dict] = []
    for att in attachments:
        if not isinstance(att, dict):
            continue
        asset_id = att.get("asset_id")
        if not asset_id:
            resolved.append(att)
            continue

        row = await db.scalar(
            select(MediaAsset).where(
                MediaAsset.id == asset_id,
                MediaAsset.user_id == user_id,
            )
        )
        if not row:
            continue

        kind = "file" if row.source == "chat_file" else "image"
        item: dict = {
            "asset_id": row.id,
            "filename": row.filename,
            "mime_type": row.mime_type,
            "kind": kind,
            "ocr_text": row.ocr_text or "",
            "vlm_caption": row.vlm_caption or "",
            "caption": row.vlm_caption or "",
        }

        if kind == "file":
            item["file_path"] = row.filename
            item["text_preview"] = row.ocr_text or ""
            resolved.append(item)
            continue

        if row.storage_uri and os.path.isfile(row.storage_uri):
            with open(row.storage_uri, "rb") as f:
                raw = f.read()
            mime = row.mime_type or "image/png"
            item["data_url"] = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
            item["url"] = f"/api/media/{row.id}/original"
            if not (item["ocr_text"] or "").strip():
                ocr = ocr_image_fast(raw)
                item["ocr_text"] = ocr.text
                item["ocr_quality"] = ocr.quality
        else:
            item["url"] = f"/api/media/{row.id}/original"

        resolved.append(item)

    return resolved

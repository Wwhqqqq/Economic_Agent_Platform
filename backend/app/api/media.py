from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.media_asset import MediaAsset
from app.ingestion.media.service import parse_chat_attachment, parse_image_bytes
from app.schemas.user_context import UserContext
from app.services.auth import get_current_user
from app.storage import get_storage

router = APIRouter(prefix="/api/media", tags=["media"])


def _require_user(user: UserContext) -> int:
    if not user.user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return user.user_id


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload image for chat attachment (not indexed into knowledge base)."""
    uid = _require_user(user)
    filename = file.filename or "image.png"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("png", "jpg", "jpeg", "webp", "gif", "bmp"):
        raise HTTPException(status_code=400, detail="仅支持 png/jpg/jpeg/webp/gif/bmp 图片")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")
    result = parse_chat_attachment(raw, uid, filename=filename)
    db.add(
        MediaAsset(
            id=result["asset_id"],
            user_id=uid,
            doc_id=None,
            filename=filename,
            mime_type=result.get("mime_type") or "image/png",
            source="chat_attachment",
            storage_uri=result.get("storage_uri") or "",
            thumbnail_uri=result.get("thumbnail_uri"),
            image_class=result.get("image_class"),
            ocr_text=result.get("ocr_text"),
            ocr_quality=result.get("ocr_quality"),
            vlm_caption=result.get("vlm_caption"),
            vlm_structured=json.dumps(result.get("vlm_structured") or {}, ensure_ascii=False),
            parse_status="ready",
        )
    )
    await db.commit()
    return {"status": "ready", **result}


@router.get("/{asset_id}")
async def get_media_metadata(
    asset_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _require_user(user)
    row = await db.scalar(
        select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.user_id == uid)
    )
    if not row:
        raise HTTPException(status_code=404, detail="媒体资源不存在")
    structured = None
    if row.vlm_structured:
        try:
            structured = json.loads(row.vlm_structured)
        except json.JSONDecodeError:
            structured = row.vlm_structured
    return {
        "asset_id": row.id,
        "filename": row.filename,
        "mime_type": row.mime_type,
        "source": row.source,
        "doc_id": row.doc_id,
        "image_class": row.image_class,
        "ocr_text": row.ocr_text,
        "ocr_quality": row.ocr_quality,
        "vlm_caption": row.vlm_caption,
        "vlm_structured": structured,
        "vlm_quality": row.vlm_quality,
        "parse_status": row.parse_status,
        "page_no": row.page_no,
        "url": f"/api/media/{row.id}/original",
        "thumbnail_url": f"/api/media/{row.id}/thumb",
    }


@router.get("/{asset_id}/original")
async def get_media_original(
    asset_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _require_user(user)
    row = await db.scalar(
        select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.user_id == uid)
    )
    if not row or not row.storage_uri or not os.path.isfile(row.storage_uri):
        raise HTTPException(status_code=404, detail="媒体资源不存在")
    return FileResponse(row.storage_uri, media_type=row.mime_type, filename=row.filename)


@router.get("/{asset_id}/thumb")
async def get_media_thumb(
    asset_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _require_user(user)
    row = await db.scalar(
        select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.user_id == uid)
    )
    if not row:
        raise HTTPException(status_code=404, detail="媒体资源不存在")
    path = row.thumbnail_uri or row.storage_uri
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="缩略图不存在")
    return FileResponse(path, media_type="image/png")


@router.post("/{asset_id}/reparse")
async def reparse_media(
    asset_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = _require_user(user)
    row = await db.scalar(
        select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.user_id == uid)
    )
    if not row or not row.storage_uri or not os.path.isfile(row.storage_uri):
        raise HTTPException(status_code=404, detail="媒体资源不存在")
    with open(row.storage_uri, "rb") as f:
        raw = f.read()
    parsed = parse_image_bytes(
        raw,
        uid,
        filename=row.filename,
        doc_id=row.doc_id,
        source=row.source or "upload",
        page_no=row.page_no,
        index=bool(row.doc_id),
    )
    row.image_class = parsed.image_class
    row.ocr_text = parsed.ocr_text
    row.ocr_quality = parsed.ocr_quality
    row.ocr_engine = parsed.ocr_engine
    row.vlm_caption = parsed.vlm_caption
    row.vlm_structured = json.dumps(parsed.vlm_structured, ensure_ascii=False) if parsed.vlm_structured else None
    row.vlm_quality = parsed.vlm_quality
    row.vlm_engine = parsed.vlm_engine
    row.parse_status = parsed.parse_status
    await db.commit()
    return {
        "status": parsed.parse_status,
        "image_class": parsed.image_class,
        "vlm_caption": parsed.vlm_caption,
        "ocr_text": parsed.ocr_text,
    }

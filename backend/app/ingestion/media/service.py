from __future__ import annotations

import io
import json
import uuid
from dataclasses import dataclass, field
from typing import Literal, Optional

from app.ingestion.chunker import chunk_text
from app.ingestion.media.image_classifier_v2 import classify_image_v2
from app.ingestion.media.ocr import ocr_image
from app.ingestion.media.vlm import (
    content_hash_bytes,
    describe_image,
    structured_to_facts,
)
from app.ingestion.ndm import NdmBlock, NormalizedDocument
from app.ingestion.pipeline_common import IngestPipelineResult, persist_ingest_artifacts
from app.rag.entity_extractor import build_document_title
from app.storage import doc_content_key, get_storage, media_asset_key, media_thumb_key

PARSER_VERSION = "media_pipeline_v2"
MIN_VLM_FACT_CONFIDENCE = 0.7

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


@dataclass
class MediaAssetRef:
    asset_id: str
    storage_uri: str
    filename: str
    mime_type: str
    thumbnail_uri: str | None = None


@dataclass
class ParseImageResult:
    asset_id: str
    storage_uri: str
    thumbnail_uri: str | None
    filename: str
    mime_type: str
    image_class: str
    skip_index: bool
    ocr_text: str
    ocr_quality: float
    ocr_engine: str
    vlm_caption: str
    vlm_structured: dict
    vlm_quality: float
    vlm_engine: str
    content_hash: str
    width: int
    height: int
    chunks: list
    facts: list = field(default_factory=list)
    plain_text: str = ""
    parse_status: str = "ready"
    page_no: int | None = None
    bbox: str | None = None


def _guess_mime(filename: str) -> str:
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }.get(ext, "application/octet-stream")


def _image_dimensions(image_bytes: bytes) -> tuple[int, int]:
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        return img.size
    except Exception:
        return 0, 0


def _make_thumbnail(image_bytes: bytes, *, max_size: int = 256) -> bytes | None:
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _figure_summary_text(
    *,
    image_class: str,
    ocr_text: str,
    vlm_caption: str,
    vlm_structured: dict,
    page_no: int | None,
) -> str:
    parts = [f"[Figure · {image_class}]"]
    if page_no:
        parts.append(f"Page {page_no}")
    if vlm_caption:
        parts.append(vlm_caption)
    elif ocr_text:
        parts.append(ocr_text)
    trends = vlm_structured.get("trends") if vlm_structured else None
    if trends:
        parts.append("趋势：" + "；".join(trends))
    figures = vlm_structured.get("key_figures") if vlm_structured else None
    if figures:
        fig_lines = []
        for fig in figures[:6]:
            label = fig.get("label", "")
            val = fig.get("value", "")
            unit = fig.get("unit") or ""
            if label:
                fig_lines.append(f"{label}: {val}{unit}")
        if fig_lines:
            parts.append("关键数值：" + "；".join(fig_lines))
    return "\n".join(parts)


class MediaAssetService:
    def upload_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: int,
        *,
        source: Literal["upload", "pdf_extract", "chat_attachment"] = "upload",
        doc_id: str | None = None,
    ) -> MediaAssetRef:
        asset_id = str(uuid.uuid4())
        key = media_asset_key(user_id, asset_id, filename)
        uri = get_storage().save_bytes(key, file_bytes)
        thumb_uri = None
        thumb_bytes = _make_thumbnail(file_bytes)
        if thumb_bytes:
            thumb_uri = get_storage().save_bytes(media_thumb_key(user_id, asset_id), thumb_bytes)
        return MediaAssetRef(
            asset_id=asset_id,
            storage_uri=uri,
            filename=filename,
            mime_type=_guess_mime(filename),
            thumbnail_uri=thumb_uri,
        )

    def persist_record_sync(
        self,
        session,
        *,
        asset_id: str,
        user_id: int,
        doc_id: str | None,
        filename: str,
        mime_type: str,
        storage_uri: str,
        source: str = "upload",
        image_class: str | None = None,
        ocr_text: str | None = None,
        ocr_quality: float | None = None,
        ocr_engine: str | None = None,
        width: int | None = None,
        height: int | None = None,
        thumbnail_uri: str | None = None,
        vlm_caption: str | None = None,
        vlm_structured: str | None = None,
        vlm_quality: float | None = None,
        vlm_engine: str | None = None,
        content_hash: str | None = None,
        parse_status: str = "ready",
        page_no: int | None = None,
        bbox: str | None = None,
    ) -> None:
        from app.db.models.media_asset import MediaAsset

        session.add(
            MediaAsset(
                id=asset_id,
                user_id=user_id,
                doc_id=doc_id,
                filename=filename,
                mime_type=mime_type,
                source=source,
                storage_uri=storage_uri,
                image_class=image_class,
                ocr_text=ocr_text,
                ocr_quality=ocr_quality,
                ocr_engine=ocr_engine,
                width=width,
                height=height,
                thumbnail_uri=thumbnail_uri,
                vlm_caption=vlm_caption,
                vlm_structured=vlm_structured,
                vlm_quality=vlm_quality,
                vlm_engine=vlm_engine,
                content_hash=content_hash,
                parse_status=parse_status,
                page_no=page_no,
                bbox=bbox,
            )
        )


def parse_image_bytes(
    image_bytes: bytes,
    user_id: int,
    *,
    filename: str = "image.png",
    doc_id: str | None = None,
    source: Literal["upload", "pdf_extract", "chat_attachment"] = "upload",
    page_no: int | None = None,
    bbox: list[float] | None = None,
    caption_hint: str = "",
    index: bool = True,
) -> ParseImageResult:
    """Unified image parse: classify → OCR → VLM → chunks/facts."""
    fname = filename or "image.png"
    media = MediaAssetService().upload_bytes(
        image_bytes, fname, user_id, source=source, doc_id=doc_id
    )
    width, height = _image_dimensions(image_bytes)
    content_hash = content_hash_bytes(image_bytes)
    ocr = ocr_image(image_bytes)
    classification = classify_image_v2(
        width=width,
        height=height,
        ocr_text=ocr.text,
        ocr_quality=ocr.quality,
        caption_hint=caption_hint,
    )

    if classification.skip_index or classification.image_class in ("decorative", "icon_logo"):
        return ParseImageResult(
            asset_id=media.asset_id,
            storage_uri=media.storage_uri,
            thumbnail_uri=media.thumbnail_uri,
            filename=fname,
            mime_type=media.mime_type,
            image_class=classification.image_class,
            skip_index=True,
            ocr_text=ocr.text,
            ocr_quality=ocr.quality,
            ocr_engine=ocr.engine,
            vlm_caption="",
            vlm_structured={},
            vlm_quality=0.0,
            vlm_engine="skipped",
            content_hash=content_hash,
            width=width,
            height=height,
            chunks=[],
            facts=[],
            plain_text="",
            parse_status="skipped",
            page_no=page_no,
            bbox=json.dumps(bbox) if bbox else None,
        )

    vlm = describe_image(
        image_bytes,
        image_class=classification.image_class,
        ocr_text=ocr.text,
    )
    summary = _figure_summary_text(
        image_class=classification.image_class,
        ocr_text=ocr.text,
        vlm_caption=vlm.caption,
        vlm_structured=vlm.structured,
        page_no=page_no,
    )
    plain_text = summary.strip() or ocr.text.strip()

    chunks: list = []
    facts: list = []
    parse_status = "ready"

    if index and plain_text:
        chunks = chunk_text(summary, doc_id or media.asset_id)
        for c in chunks:
            c.content_type = "figure_summary"
            c.section_path = c.section_path or (f"Page {page_no}" if page_no else "Figure")
            if page_no:
                c.page_range = str(page_no)
        if vlm.structured and vlm.quality >= MIN_VLM_FACT_CONFIDENCE and doc_id:
            facts = structured_to_facts(
                vlm.structured,
                doc_id=doc_id,
                asset_id=media.asset_id,
                page_no=page_no,
                min_confidence=vlm.quality,
            )
    elif not plain_text:
        parse_status = "needs_review"

    return ParseImageResult(
        asset_id=media.asset_id,
        storage_uri=media.storage_uri,
        thumbnail_uri=media.thumbnail_uri,
        filename=fname,
        mime_type=media.mime_type,
        image_class=classification.image_class,
        skip_index=False,
        ocr_text=ocr.text,
        ocr_quality=ocr.quality,
        ocr_engine=ocr.engine,
        vlm_caption=vlm.caption,
        vlm_structured=vlm.structured,
        vlm_quality=vlm.quality,
        vlm_engine=vlm.engine,
        content_hash=content_hash,
        width=width,
        height=height,
        chunks=chunks,
        facts=facts,
        plain_text=plain_text,
        parse_status=parse_status,
        page_no=page_no,
        bbox=json.dumps(bbox) if bbox else None,
    )


def parse_chat_attachment(image_bytes: bytes, user_id: int, *, filename: str = "image.png") -> dict:
    """Parse image for chat (no knowledge indexing)."""
    import base64

    parsed = parse_image_bytes(
        image_bytes,
        user_id,
        filename=filename,
        source="chat_attachment",
        doc_id=None,
        index=False,
    )
    b64 = base64.b64encode(image_bytes).decode("ascii")
    mime = parsed.mime_type or "image/png"
    return {
        "asset_id": parsed.asset_id,
        "filename": parsed.filename,
        "mime_type": mime,
        "image_class": parsed.image_class,
        "ocr_text": parsed.ocr_text,
        "ocr_quality": parsed.ocr_quality,
        "vlm_caption": parsed.vlm_caption,
        "vlm_structured": parsed.vlm_structured,
        "storage_uri": parsed.storage_uri,
        "thumbnail_uri": parsed.thumbnail_uri,
        "data_url": f"data:{mime};base64,{b64}",
        "url": f"/api/media/{parsed.asset_id}/original",
        "thumbnail_url": f"/api/media/{parsed.asset_id}/thumb",
    }


def prepare_media_ingest(
    image_bytes: bytes,
    doc_id: str,
    user_id: int,
    *,
    filename: str | None = None,
    metadata: dict | None = None,
) -> IngestPipelineResult:
    fname = filename or "image.png"
    parsed = parse_image_bytes(
        image_bytes,
        user_id,
        filename=fname,
        doc_id=doc_id,
        source="upload",
        index=True,
    )

    if parsed.skip_index:
        ndm = NormalizedDocument(
            doc_id=doc_id,
            user_id=user_id,
            source_type="image",
            title=fname,
            filename=fname,
            parse_metadata={
                "parser_version": PARSER_VERSION,
                "image_class": parsed.image_class,
                "skipped": True,
            },
        )
        result = IngestPipelineResult(
            doc_id=doc_id,
            title=fname,
            ndm=ndm,
            chunks=[],
            ndm_uri="",
            content_uri=parsed.storage_uri,
            parser_version=PARSER_VERSION,
            parse_status="skipped",
            quality_score=parsed.ocr_quality,
            plain_text="",
            media_asset_id=parsed.asset_id,
            media_asset_uri=parsed.storage_uri,
            media_filename=fname,
            media_mime_type=parsed.mime_type,
        )
        persist_ingest_artifacts(result, user_id, plain_text="")
        return result

    title = build_document_title(parsed.plain_text, doc_id) if parsed.plain_text else fname
    ndm = NormalizedDocument(
        doc_id=doc_id,
        user_id=user_id,
        source_type="image",
        title=title,
        filename=fname,
        blocks=[
            NdmBlock(
                block_id=f"fig_{parsed.asset_id[:8]}",
                type="figure",
                text=parsed.plain_text,
                section_path=["Figure"],
                role="body",
            )
        ],
        doc_metadata={
            "media_asset_id": parsed.asset_id,
            "image_class": parsed.image_class,
            **(metadata or {}),
        },
        parse_metadata={
            "parser_version": PARSER_VERSION,
            "ocr_engine": parsed.ocr_engine,
            "ocr_quality": parsed.ocr_quality,
            "image_class": parsed.image_class,
            "vlm_engine": parsed.vlm_engine,
            "vlm_quality": parsed.vlm_quality,
            "vlm_caption": parsed.vlm_caption,
            "vlm_structured": json.dumps(parsed.vlm_structured, ensure_ascii=False) if parsed.vlm_structured else None,
            "width": parsed.width,
            "height": parsed.height,
        },
    )

    if parsed.plain_text:
        get_storage().save_text(doc_content_key(user_id, doc_id), parsed.plain_text)

    result = IngestPipelineResult(
        doc_id=doc_id,
        title=title,
        ndm=ndm,
        chunks=parsed.chunks,
        ndm_uri="",
        content_uri=parsed.storage_uri,
        parser_version=PARSER_VERSION,
        parse_status=parsed.parse_status,
        quality_score=max(parsed.ocr_quality, parsed.vlm_quality),
        plain_text=parsed.plain_text,
        facts=parsed.facts,
        media_asset_id=parsed.asset_id,
        media_asset_uri=parsed.storage_uri,
        media_filename=fname,
        media_mime_type=parsed.mime_type,
        error_message=None if parsed.plain_text else "图片未能解析出有效内容",
    )
    persist_ingest_artifacts(result, user_id, plain_text=parsed.plain_text)
    return result

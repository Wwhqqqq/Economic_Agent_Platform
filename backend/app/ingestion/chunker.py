from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass

from app.ingestion.ndm import NdmBlock, NormalizedDocument

# Target doc 01: 300-800 tokens; use char budget for CJK-heavy text (~1.5 chars/token)
DEFAULT_MAX_TOKENS = 600
DEFAULT_MIN_TOKENS = 80
DEFAULT_OVERLAP_RATIO = 0.12
CHARS_PER_TOKEN = 2


@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    seq: int
    text: str
    token_count: int
    content_type: str
    section_path: str
    content_hash: str
    block_ids: list[str]
    page_range: str = ""


def estimate_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    rest = max(0, len(text) - cjk)
    return cjk + max(1, rest // 4)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _max_chars(max_tokens: int) -> int:
    return max_tokens * CHARS_PER_TOKEN


def _overlap_chars(max_tokens: int, ratio: float) -> int:
    return int(_max_chars(max_tokens) * ratio)


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _is_markdown(text: str) -> bool:
    return bool(re.search(r"(?m)^#{1,6}\s+\S", text)) or text.lstrip().startswith("---")


def chunk_markdown(
    text: str,
    doc_id: str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
) -> list[ChunkRecord]:
    max_chars = _max_chars(max_tokens)
    overlap_chars = _overlap_chars(max_tokens, overlap_ratio)
    chunks: list[ChunkRecord] = []
    section_stack: list[str] = []
    buffer = ""
    buffer_blocks: list[str] = []
    seq = 0

    def flush(with_overlap: bool = False) -> None:
        nonlocal buffer, buffer_blocks, seq
        body = buffer.strip()
        if not body or estimate_tokens(body) < DEFAULT_MIN_TOKENS // 2:
            buffer = ""
            buffer_blocks = []
            return
        section = " > ".join(section_stack) if section_stack else ""
        cid = str(uuid.uuid4())
        chunks.append(
            ChunkRecord(
                chunk_id=cid,
                doc_id=doc_id,
                seq=seq,
                text=body,
                token_count=estimate_tokens(body),
                content_type="paragraph",
                section_path=section,
                content_hash=content_hash(body),
                block_ids=list(buffer_blocks),
            )
        )
        seq += 1
        if with_overlap and overlap_chars > 0 and len(body) > overlap_chars:
            buffer = body[-overlap_chars:]
            buffer_blocks = [buffer_blocks[-1]] if buffer_blocks else []
        else:
            buffer = ""
            buffer_blocks = []

    for line in text.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if heading:
            flush(with_overlap=False)
            level = len(heading.group(1))
            title = heading.group(2).strip()
            section_stack = section_stack[: level - 1]
            section_stack.append(title)
            continue

        line_stripped = line.strip()
        if not line_stripped:
            if buffer and len(buffer) >= max_chars:
                flush(with_overlap=True)
            continue

        candidate = f"{buffer}\n{line_stripped}".strip() if buffer else line_stripped
        if len(candidate) > max_chars:
            flush(with_overlap=True)
            buffer = line_stripped
            buffer_blocks = [f"b{seq}"]
        else:
            buffer = candidate
            if not buffer_blocks:
                buffer_blocks = [f"b{seq}"]

    flush(with_overlap=False)
    return chunks


def chunk_plain_text(
    text: str,
    doc_id: str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
) -> list[ChunkRecord]:
    max_chars = _max_chars(max_tokens)
    overlap_chars = _overlap_chars(max_tokens, overlap_ratio)
    paragraphs = _split_paragraphs(text)
    chunks: list[ChunkRecord] = []
    buffer = ""
    seq = 0

    def flush(with_overlap: bool = False) -> None:
        nonlocal buffer, seq
        body = buffer.strip()
        if not body:
            buffer = ""
            return
        cid = str(uuid.uuid4())
        chunks.append(
            ChunkRecord(
                chunk_id=cid,
                doc_id=doc_id,
                seq=seq,
                text=body,
                token_count=estimate_tokens(body),
                content_type="paragraph",
                section_path="",
                content_hash=content_hash(body),
                block_ids=[f"p{seq}"],
            )
        )
        seq += 1
        if with_overlap and overlap_chars > 0 and len(body) > overlap_chars:
            buffer = body[-overlap_chars:]
        else:
            buffer = ""

    for para in paragraphs:
        if len(para) > max_chars:
            flush(with_overlap=False)
            start = 0
            while start < len(para):
                end = min(len(para), start + max_chars)
                piece = para[start:end]
                cid = str(uuid.uuid4())
                chunks.append(
                    ChunkRecord(
                        chunk_id=cid,
                        doc_id=doc_id,
                        seq=seq,
                        text=piece,
                        token_count=estimate_tokens(piece),
                        content_type="paragraph",
                        section_path="",
                        content_hash=content_hash(piece),
                        block_ids=[f"p{seq}"],
                    )
                )
                seq += 1
                start = end - overlap_chars if end < len(para) else end
            continue

        candidate = f"{buffer}\n\n{para}".strip() if buffer else para
        if len(candidate) > max_chars:
            flush(with_overlap=True)
            buffer = para
        else:
            buffer = candidate

    flush(with_overlap=False)
    return chunks


def chunk_text(
    text: str,
    doc_id: str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
) -> list[ChunkRecord]:
    if not text.strip():
        return []
    if _is_markdown(text):
        return chunk_markdown(text, doc_id, max_tokens=max_tokens, overlap_ratio=overlap_ratio)
    return chunk_plain_text(text, doc_id, max_tokens=max_tokens, overlap_ratio=overlap_ratio)


def build_ndm_from_text(
    content: str,
    doc_id: str,
    user_id: int,
    *,
    filename: str | None = None,
    title: str = "",
) -> NormalizedDocument:
    blocks: list[NdmBlock] = []
    if _is_markdown(content):
        section_stack: list[str] = []
        for i, line in enumerate(content.splitlines()):
            heading = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if heading:
                level = len(heading.group(1))
                section_stack = section_stack[: level - 1]
                section_stack.append(heading.group(2).strip())
                blocks.append(
                    NdmBlock(
                        block_id=f"md_{i}",
                        type="heading",
                        text=heading.group(2).strip(),
                        section_path=list(section_stack),
                    )
                )
                continue
            if line.strip():
                blocks.append(
                    NdmBlock(
                        block_id=f"md_{i}",
                        type="paragraph",
                        text=line.strip(),
                        section_path=list(section_stack),
                    )
                )
    else:
        for i, para in enumerate(_split_paragraphs(content)):
            blocks.append(
                NdmBlock(
                    block_id=f"p_{i}",
                    type="paragraph",
                    text=para,
                    section_path=[],
                )
            )

    return NormalizedDocument(
        doc_id=doc_id,
        user_id=user_id,
        source_type="text",
        title=title,
        filename=filename,
        blocks=blocks,
        parse_metadata={"parser_version": "text_v1", "chunk_strategy": "markdown" if _is_markdown(content) else "plain"},
    )

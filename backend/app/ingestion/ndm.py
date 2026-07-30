from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class NdmBlock:
    block_id: str
    type: str
    text: str
    section_path: list[str] = field(default_factory=list)
    page_no: int | None = None
    bbox: list[float] | None = None
    role: str = "body"


@dataclass
class NormalizedDocument:
    doc_id: str
    user_id: int
    source_type: str = "text"
    title: str = ""
    language: str = "zh-CN"
    filename: Optional[str] = None
    blocks: list[NdmBlock] = field(default_factory=list)
    doc_metadata: dict[str, Any] = field(default_factory=dict)
    parse_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "user_id": self.user_id,
            "source": {
                "source_type": self.source_type,
                "filename": self.filename,
            },
            "doc_metadata": {
                "title": self.title,
                "language": self.language,
                **self.doc_metadata,
            },
            "parse_metadata": self.parse_metadata,
            "blocks": [
                {
                    "block_id": b.block_id,
                    "type": b.type,
                    "text": b.text,
                    "section_path": b.section_path,
                    "page_no": b.page_no,
                    "bbox": b.bbox,
                    "role": b.role,
                }
                for b in self.blocks
            ],
        }

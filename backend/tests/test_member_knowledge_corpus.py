"""Validate member knowledge corpus manifest and files."""
from __future__ import annotations

import json
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "member_knowledge"


def test_manifest_documents_exist():
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    docs = manifest["documents"]
    assert len(docs) >= 15
    for entry in docs:
        path = CORPUS_DIR / entry["file"]
        assert path.is_file(), f"missing corpus file: {entry['file']}"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 500, f"corpus too short: {entry['file']}"
        assert entry["doc_id"].startswith("member-")


def test_manifest_has_sources():
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["documents"]:
        assert entry.get("sources"), f"missing sources: {entry['doc_id']}"
        assert entry.get("title")

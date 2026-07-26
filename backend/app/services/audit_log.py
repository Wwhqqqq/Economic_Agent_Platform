"""
Simple audit logging — JSON Lines in data/audit.log
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_FILE = Path(__file__).resolve().parents[3] / "data" / "audit.log"


def _ensure_dir() -> None:
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)


def log_action(action: str, user: str = "anonymous", detail: dict[str, Any] | None = None) -> None:
    _ensure_dir()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user": user,
        "detail": detail or {},
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_logs(limit: int = 100) -> list[dict]:
    if not AUDIT_FILE.exists():
        return []
    lines = AUDIT_FILE.read_text(encoding="utf-8").strip().splitlines()
    logs = []
    for line in lines[-limit:]:
        try:
            logs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(logs))

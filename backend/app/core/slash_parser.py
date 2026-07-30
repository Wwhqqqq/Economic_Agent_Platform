"""Parse `/skill_name optional message` slash commands."""
from __future__ import annotations

import re
from typing import Optional

SLASH_PATTERN = re.compile(r"^/([a-z][a-z0-9_]{1,63})(?:\s+(.*))?$", re.DOTALL)


def parse_slash_command(text: str) -> tuple[Optional[str], str]:
    """Return (skill_name, remaining_message). skill_name is None if not a slash command."""
    stripped = text.strip()
    match = SLASH_PATTERN.match(stripped)
    if not match:
        return None, text
    skill_name = match.group(1)
    remainder = (match.group(2) or "").strip()
    return skill_name, remainder

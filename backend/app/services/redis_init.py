"""Initialize Redis key layout on startup (Phase 0/1)."""
from __future__ import annotations

from app.db.redis_client import get_redis
from app.db.redis_keys import META_SCHEMA_VERSION, SCHEMA_VERSION


async def init_redis_layout() -> None:
    """Write schema version marker; future phases add blacklist / rate-limit helpers."""
    client = get_redis()
    await client.set(META_SCHEMA_VERSION, SCHEMA_VERSION)

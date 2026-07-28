"""Redis client for cache, rate limit, and token blacklist (Phase 3+)."""
from __future__ import annotations

import os
from typing import Optional

import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def ping_redis() -> dict:
    try:
        client = get_redis()
        pong = await client.ping()
        return {"status": "up" if pong else "down", "url": REDIS_URL.split("@")[-1]}
    except Exception as exc:
        return {"status": "down", "error": str(exc)}


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None

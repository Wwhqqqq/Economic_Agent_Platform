"""Email verification code generation, storage, and validation."""
from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Optional

from app.db.redis_client import get_redis

CODE_TTL_SECONDS = int(os.getenv("VERIFICATION_CODE_TTL", "60"))
COOLDOWN_SECONDS = int(os.getenv("VERIFICATION_COOLDOWN", "60"))
MAX_ATTEMPTS = int(os.getenv("VERIFICATION_MAX_ATTEMPTS", "5"))
IP_SEND_LIMIT_PER_HOUR = int(os.getenv("VERIFICATION_IP_LIMIT_HOUR", "10"))

# Fallback when Redis unavailable (dev / single process)
_memory_store: dict[str, dict[str, Any]] = {}
_memory_cooldown: dict[str, float] = {}
_ip_counters: dict[str, list[float]] = {}


def _code_key(email: str, purpose: str) -> str:
    return f"verify:{purpose}:{email.lower()}"


def _cooldown_key(email: str, purpose: str) -> str:
    return f"verify:cooldown:{purpose}:{email.lower()}"


def _generate_code() -> str:
    return f"{random.randint(0, 9999):04d}"


async def _redis_get(key: str) -> Optional[str]:
    try:
        client = get_redis()
        return await client.get(key)
    except Exception:
        return None


async def _redis_set(key: str, value: str, ex: int) -> bool:
    try:
        client = get_redis()
        await client.set(key, value, ex=ex)
        return True
    except Exception:
        return False


async def _redis_delete(key: str) -> None:
    try:
        client = get_redis()
        await client.delete(key)
    except Exception:
        pass


def _check_ip_limit(ip: Optional[str]) -> tuple[bool, int]:
    if not ip:
        return True, 0
    now = time.time()
    window_start = now - 3600
    hits = [t for t in _ip_counters.get(ip, []) if t >= window_start]
    _ip_counters[ip] = hits
    if len(hits) >= IP_SEND_LIMIT_PER_HOUR:
        return False, 0
    hits.append(now)
    _ip_counters[ip] = hits
    return True, 0


async def get_cooldown_remaining(email: str, purpose: str = "register") -> int:
    key = _cooldown_key(email, purpose)
    raw = await _redis_get(key)
    if raw is not None:
        try:
            return max(0, int(raw))
        except ValueError:
            return 0
    mem = _memory_cooldown.get(key)
    if mem is None:
        return 0
    return max(0, int(mem - time.time()))


async def issue_verification_code(
    email: str,
    purpose: str = "register",
    client_ip: Optional[str] = None,
) -> tuple[str, int]:
    """Create code, store with TTL, set cooldown. Returns (code, retry_after_seconds)."""
    remaining = await get_cooldown_remaining(email, purpose)
    if remaining > 0:
        raise ValueError(f"SEND_TOO_FREQUENT:{remaining}")

    ok, _ = _check_ip_limit(client_ip)
    if not ok:
        raise ValueError("SEND_TOO_FREQUENT:0")

    code = _generate_code()
    payload = json.dumps({"code": code, "attempts": 0})
    store_key = _code_key(email, purpose)
    cooldown_key = _cooldown_key(email, purpose)

    stored = await _redis_set(store_key, payload, CODE_TTL_SECONDS)
    if stored:
        await _redis_set(cooldown_key, str(COOLDOWN_SECONDS), COOLDOWN_SECONDS)
    else:
        _memory_store[store_key] = {
            "code": code,
            "attempts": 0,
            "expires_at": time.time() + CODE_TTL_SECONDS,
        }
        _memory_cooldown[cooldown_key] = time.time() + COOLDOWN_SECONDS

    return code, COOLDOWN_SECONDS


async def verify_and_consume_code(
    email: str,
    code: str,
    purpose: str = "register",
    *,
    consume: bool = True,
) -> tuple[bool, str]:
    """
    Verify code. Returns (ok, error_code).
    error_code: VERIFICATION_CODE_INVALID | VERIFICATION_CODE_EXPIRED | VERIFICATION_CODE_MAX_ATTEMPTS
    """
    store_key = _code_key(email, purpose)
    raw = await _redis_get(store_key)

    record: Optional[dict[str, Any]] = None
    use_redis = raw is not None

    if use_redis:
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            record = None
    else:
        mem = _memory_store.get(store_key)
        if mem and mem.get("expires_at", 0) >= time.time():
            record = {"code": mem["code"], "attempts": mem.get("attempts", 0)}
        elif mem:
            del _memory_store[store_key]
            return False, "VERIFICATION_CODE_EXPIRED"

    if not record:
        return False, "VERIFICATION_CODE_EXPIRED"

    attempts = int(record.get("attempts", 0))
    if attempts >= MAX_ATTEMPTS:
        await _redis_delete(store_key)
        _memory_store.pop(store_key, None)
        return False, "VERIFICATION_CODE_MAX_ATTEMPTS"

    if record.get("code") != code.strip():
        attempts += 1
        record["attempts"] = attempts
        if use_redis:
            ttl = CODE_TTL_SECONDS
            await _redis_set(store_key, json.dumps(record), ttl)
        else:
            if store_key in _memory_store:
                _memory_store[store_key]["attempts"] = attempts
        if attempts >= MAX_ATTEMPTS:
            return False, "VERIFICATION_CODE_MAX_ATTEMPTS"
        return False, "VERIFICATION_CODE_INVALID"

    if consume:
        await _redis_delete(store_key)
        _memory_store.pop(store_key, None)

    return True, ""

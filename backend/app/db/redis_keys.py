"""Redis key namespaces for multi-user features (Phase 0/1 layout).

Redis has no tables; keys follow a fixed prefix convention so Phase 3+
(blacklist, rate limit, cache) can share one schema.
"""
from __future__ import annotations

import os

APP_PREFIX = os.getenv("REDIS_KEY_PREFIX", "agent")

# Phase 3+: JWT logout blacklist — SET member = jti, TTL = token remaining life
JWT_BLACKLIST = f"{APP_PREFIX}:jwt:blacklist"  # suffix :{jti}

# Phase 3+: login/register rate limit — INCR with EXPIRE
RATE_LIMIT_LOGIN = f"{APP_PREFIX}:ratelimit:login"  # suffix :{ip}
RATE_LIMIT_REGISTER = f"{APP_PREFIX}:ratelimit:register"

# Phase 3+: optional user type cache
USER_TYPE_CACHE = f"{APP_PREFIX}:user:type"  # suffix :{user_id}

# Phase 0 meta — schema version marker (string)
META_SCHEMA_VERSION = f"{APP_PREFIX}:meta:schema_version"

SCHEMA_VERSION = "phase1-v1"


def jwt_blacklist_key(jti: str) -> str:
    return f"{JWT_BLACKLIST}:{jti}"


def rate_limit_login_key(ip: str) -> str:
    return f"{RATE_LIMIT_LOGIN}:{ip}"


def rate_limit_register_key(ip: str) -> str:
    return f"{RATE_LIMIT_REGISTER}:{ip}"


def user_type_cache_key(user_id: int) -> str:
    return f"{USER_TYPE_CACHE}:{user_id}"

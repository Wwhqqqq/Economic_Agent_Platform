"""
Lightweight JWT auth — optional via AUTH_ENABLED
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import Depends, HTTPException, Header

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin123")
JWT_SECRET = os.getenv("JWT_SECRET", "agent-platform-dev-secret-change-me")


def _b64url(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_token(username: str, ttl_seconds: int = 86400) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(
        json.dumps({"sub": username, "exp": int(time.time()) + ttl_seconds}).encode()
    )
    sig = hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def verify_token(token: str) -> Optional[str]:
    try:
        header, payload, signature = token.split(".")
        expected = hmac.new(
            JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64url(expected), signature):
            return None
        import base64
        pad = "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload + pad))
        if data.get("exp", 0) < time.time():
            return None
        return data.get("sub")
    except Exception:
        return None


def authenticate(username: str, password: str) -> bool:
    return username == AUTH_USERNAME and password == AUTH_PASSWORD


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> str:
    if not AUTH_ENABLED:
        return "anonymous"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期")
    return user


async def require_admin(user: str = Depends(get_current_user)) -> str:
    if AUTH_ENABLED and user != AUTH_USERNAME:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user

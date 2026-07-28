"""
Authentication — JWT, password hashing, user resolution.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.user import User
from app.schemas.user_context import UserContext

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
JWT_SECRET = os.getenv("JWT_SECRET", "agent-platform-dev-secret-change-me")
JWT_TTL_SECONDS = int(os.getenv("JWT_TTL_SECONDS", "86400"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))

# Legacy env fallback when DB unavailable
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin123")


def _b64url(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_token(user: User) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_data = {
        "sub": user.id,
        "username": user.username,
        "user_type": user.user_type,
        "exp": int(time.time()) + JWT_TTL_SECONDS,
        "iat": int(time.time()),
        "jti": os.urandom(8).hex(),
    }
    if user.membership_expires_at:
        payload_data["membership_expires_at"] = int(user.membership_expires_at.timestamp())
    payload = _b64url(json.dumps(payload_data).encode())
    sig = hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def verify_token(token: str) -> Optional[dict]:
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
        return data
    except Exception:
        return None


def _normalize_membership(user: User) -> User:
    """Downgrade expired member to regular."""
    if user.user_type == "member" and user.membership_expires_at:
        now = datetime.now(timezone.utc)
        expires = user.membership_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            user.user_type = "regular"
            user.membership_expires_at = None
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if user.status != "active":
        return None
    if user.locked_until and user.locked_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
        return None
    if not verify_password(password, user.password_hash):
        user.login_attempts += 1
        if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
            from datetime import timedelta
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        await db.flush()
        return None
    user.login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    user = _normalize_membership(user)
    await db.flush()
    return user


async def register_user(
    db: AsyncSession,
    username: str,
    password: str,
    email: Optional[str] = None,
    user_type: str = "regular",
) -> User:
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise ValueError("用户名已存在")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        user_type=user_type,
        status="active",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user = _normalize_membership(user)
    return user


def user_to_context(user: User) -> UserContext:
    user = _normalize_membership(user)
    return UserContext(
        user_id=user.id,
        username=user.username,
        user_type=user.user_type,
        membership_expires_at=user.membership_expires_at,
    )


async def resolve_user_context(
    db: AsyncSession,
    authorization: Optional[str],
) -> UserContext:
    if not AUTH_ENABLED:
        return UserContext.anonymous()

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")

    token = authorization[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="无效 Token")

    user = await get_user_by_id(db, int(user_id))
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="用户不可用")

    return user_to_context(user)


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    return await resolve_user_context(db, authorization)


async def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    if not AUTH_ENABLED:
        return UserContext.anonymous()
    try:
        return await resolve_user_context(db, authorization)
    except HTTPException:
        return UserContext.anonymous()


async def require_member(user: UserContext = Depends(get_current_user)) -> UserContext:
    if not AUTH_ENABLED:
        return user
    if not user.is_member:
        raise HTTPException(status_code=403, detail="该功能需开通会员")
    return user


# Legacy alias — 无管理员角色，登录用户即可（Phase 1 兼容旧 settings 路由）
async def require_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    if AUTH_ENABLED and user.user_id == 0:
        raise HTTPException(status_code=401, detail="未登录")
    return user

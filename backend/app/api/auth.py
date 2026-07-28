"""Authentication API"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth import (
    AUTH_ENABLED,
    authenticate_user,
    create_token,
    get_current_user,
    register_user,
    user_to_context,
)
from app.services.audit_log import log_action
from app.schemas.user_context import UserContext

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: Optional[str] = None


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, req.username, req.password, req.email)
        token = create_token(user)
        log_action("auth.register", req.username)
        ctx = user_to_context(user)
        return {
            "success": True,
            "token": token,
            "user_id": ctx.user_id,
            "username": ctx.username,
            "user_type": ctx.user_type,
        }
    except ValueError as e:
        return {"success": False, "message": str(e)}


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, req.username, req.password)
    if not user:
        return {"success": False, "message": "用户名或密码错误"}
    token = create_token(user)
    log_action("auth.login", req.username)
    ctx = user_to_context(user)
    return {
        "success": True,
        "token": token,
        "user_id": ctx.user_id,
        "username": ctx.username,
        "user_type": ctx.user_type,
        "membership_expires_at": (
            ctx.membership_expires_at.isoformat() if ctx.membership_expires_at else None
        ),
    }


@router.get("/config")
async def auth_config():
    """Public auth flags for frontend bootstrap (no token required)."""
    return {"auth_enabled": AUTH_ENABLED}


@router.get("/me")
async def me(user: UserContext = Depends(get_current_user)):
    return {
        "user_id": user.user_id,
        "username": user.username,
        "user_type": user.user_type,
        "auth_enabled": AUTH_ENABLED,
        "membership_expires_at": (
            user.membership_expires_at.isoformat() if user.membership_expires_at else None
        ),
    }

"""Authentication API"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.user import User
from app.core.validators import validate_email, validate_password, validate_username, validate_verification_code
from app.services.auth import (
    AUTH_ENABLED,
    authenticate_user,
    create_token,
    email_exists,
    get_current_user,
    get_user_by_id,
    hash_password,
    register_user,
    user_to_context,
    username_exists,
    verify_password,
)
from app.services.audit_log import log_action
from app.services.email_service import send_verification_email
from app.services.verification import get_cooldown_remaining, issue_verification_code, verify_and_consume_code
from app.services.membership_service import apply_registration_trial
from app.schemas.user_context import UserContext

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class SendVerificationCodeRequest(BaseModel):
    email: str
    purpose: Literal["register"] = "register"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str
    password: str = Field(min_length=6, max_length=128)
    verification_code: str = Field(min_length=4, max_length=4)


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _error(code: str, message: str, field: Optional[str] = None, **extra):
    body = {"success": False, "code": code, "message": message}
    if field:
        body["field"] = field
    body.update(extra)
    return body


@router.post("/send-verification-code")
async def send_verification_code(
    req: SendVerificationCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    email = req.email.strip().lower()
    ok, msg = validate_email(email)
    if not ok:
        return _error("EMAIL_INVALID", msg or "请输入有效的邮箱地址", "email")

    if await email_exists(db, email):
        return _error("EMAIL_ALREADY_REGISTERED", "该邮箱已被注册", "email")

    remaining = await get_cooldown_remaining(email, req.purpose)
    if remaining > 0:
        return _error(
            "SEND_TOO_FREQUENT",
            "发送过于频繁，请稍后再试",
            "email",
            retry_after_seconds=remaining,
        )

    try:
        code, retry_after = await issue_verification_code(
            email, req.purpose, client_ip=_client_ip(request)
        )
        await send_verification_email(email, code)
        log_action("auth.verification_sent", email)
        return {
            "success": True,
            "message": "验证码已发送",
            "retry_after_seconds": retry_after,
        }
    except ValueError as exc:
        err = str(exc)
        if err.startswith("SEND_TOO_FREQUENT:"):
            secs = int(err.split(":")[1] or "60")
            return _error(
                "SEND_TOO_FREQUENT",
                "发送过于频繁，请稍后再试",
                "email",
                retry_after_seconds=secs,
            )
        return _error("SEND_FAILED", err, "email")
    except RuntimeError as exc:
        return _error("MAIL_SEND_FAILED", str(exc), "email")
    except Exception:
        return _error("MAIL_SEND_FAILED", "邮件发送失败，请稍后重试", "email")


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    username = req.username.strip()
    email = req.email.strip().lower()
    password = req.password
    code = req.verification_code.strip()

    ok, msg = validate_username(username)
    if not ok:
        return _error("USERNAME_INVALID", msg or "用户名格式不正确", "username")

    ok, msg = validate_email(email)
    if not ok:
        return _error("EMAIL_INVALID", msg or "请输入有效的邮箱地址", "email")

    ok, msg = validate_password(password)
    if not ok:
        return _error(
            "PASSWORD_INVALID",
            msg or "密码只能包含字母、数字和下划线，至少 6 位",
            "password",
        )

    ok, msg = validate_verification_code(code)
    if not ok:
        return _error("VERIFICATION_CODE_INVALID", msg or "请输入 4 位数字验证码", "verification_code")

    if await username_exists(db, username):
        return _error("USERNAME_TAKEN", "用户名已被占用", "username")

    if await email_exists(db, email):
        return _error("EMAIL_TAKEN", "该邮箱已被注册", "email")

    verified, err_code = await verify_and_consume_code(email, code, "register", consume=True)
    if not verified:
        if err_code == "VERIFICATION_CODE_EXPIRED":
            return _error("VERIFICATION_CODE_EXPIRED", "验证码已过期，请重新获取", "verification_code")
        if err_code == "VERIFICATION_CODE_MAX_ATTEMPTS":
            return _error("VERIFICATION_CODE_INVALID", "验证码错误次数过多，请重新获取", "verification_code")
        log_action("auth.verification_failed", email)
        return _error("VERIFICATION_CODE_INVALID", "验证码错误", "verification_code")

    try:
        user = await register_user(db, username, password, email)
        is_trial = await apply_registration_trial(db, user)
        await db.commit()
        token = create_token(user)
        log_action("auth.register", username)
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
            "is_trial": is_trial,
        }
    except ValueError as exc:
        err = str(exc)
        if err.startswith("USERNAME_TAKEN:"):
            return _error("USERNAME_TAKEN", err.split(":", 1)[1], "username")
        if err.startswith("EMAIL_TAKEN:"):
            return _error("EMAIL_TAKEN", err.split(":", 1)[1], "email")
        if err.startswith("USERNAME_INVALID:"):
            return _error("USERNAME_INVALID", err.split(":", 1)[1], "username")
        if err.startswith("EMAIL_INVALID:"):
            return _error("EMAIL_INVALID", err.split(":", 1)[1], "email")
        if err.startswith("PASSWORD_INVALID:"):
            return _error("PASSWORD_INVALID", err.split(":", 1)[1], "password")
        return _error("REGISTER_FAILED", err.split(":", 1)[-1], "username")


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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("/me")
async def me(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = {
        "user_id": user.user_id,
        "username": user.username,
        "user_type": user.user_type,
        "auth_enabled": AUTH_ENABLED,
        "membership_expires_at": (
            user.membership_expires_at.isoformat() if user.membership_expires_at else None
        ),
        "email": None,
        "status": "active",
        "created_at": None,
        "last_login_at": None,
    }
    if user.user_id:
        db_user = await get_user_by_id(db, user.user_id)
        if db_user:
            profile["email"] = db_user.email
            profile["status"] = db_user.status
            profile["created_at"] = db_user.created_at.isoformat() if db_user.created_at else None
            profile["last_login_at"] = (
                db_user.last_login_at.isoformat() if db_user.last_login_at else None
            )
    return profile


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.user_id:
        return {"success": False, "code": "UNAUTHORIZED", "message": "未登录"}

    ok, msg = validate_password(req.new_password)
    if not ok:
        return {"success": False, "code": "PASSWORD_INVALID", "message": msg, "field": "new_password"}

    db_user = await get_user_by_id(db, user.user_id)
    if not db_user:
        return {"success": False, "code": "UNAUTHORIZED", "message": "用户不存在"}

    if not verify_password(req.current_password, db_user.password_hash):
        return {
            "success": False,
            "code": "INVALID_CURRENT_PASSWORD",
            "message": "当前密码不正确",
            "field": "current_password",
        }

    db_user.password_hash = hash_password(req.new_password)
    await db.flush()
    log_action("auth.password_change", user.username, {})
    return {"success": True, "message": "密码已更新"}


class SendBindEmailRequest(BaseModel):
    email: str


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    email: Optional[str] = None
    verification_code: Optional[str] = None


@router.post("/send-bind-email-code")
async def send_bind_email_code(
    req: SendBindEmailRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.user_id:
        return _error("UNAUTHORIZED", "未登录")

    email = req.email.strip().lower()
    ok, msg = validate_email(email)
    if not ok:
        return _error("EMAIL_INVALID", msg or "请输入有效的邮箱地址", "email")

    result = await db.execute(
        select(User).where(User.email == email, User.id != user.user_id)
    )
    if result.scalar_one_or_none():
        return _error("EMAIL_TAKEN", "该邮箱已被其他账号使用", "email")

    remaining = await get_cooldown_remaining(email, "bind_email")
    if remaining > 0:
        return _error(
            "SEND_TOO_FREQUENT",
            "发送过于频繁，请稍后再试",
            "email",
            retry_after_seconds=remaining,
        )

    try:
        code, retry_after = await issue_verification_code(
            email, "bind_email", client_ip=_client_ip(request)
        )
        await send_verification_email(email, code)
        log_action("auth.bind_email_sent", user.username, {"email": email})
        return {
            "success": True,
            "message": "验证码已发送",
            "retry_after_seconds": retry_after,
        }
    except ValueError as exc:
        err = str(exc)
        if err.startswith("SEND_TOO_FREQUENT:"):
            secs = int(err.split(":")[1] or "60")
            return _error(
                "SEND_TOO_FREQUENT",
                "发送过于频繁，请稍后再试",
                "email",
                retry_after_seconds=secs,
            )
        return _error("SEND_FAILED", err, "email")
    except RuntimeError as exc:
        return _error("MAIL_SEND_FAILED", str(exc), "email")
    except Exception:
        return _error("MAIL_SEND_FAILED", "邮件发送失败，请稍后重试", "email")


@router.patch("/profile")
async def update_profile(
    req: UpdateProfileRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.user_id:
        return _error("UNAUTHORIZED", "未登录")

    db_user = await get_user_by_id(db, user.user_id)
    if not db_user:
        return _error("UNAUTHORIZED", "用户不存在")

    token: Optional[str] = None

    if req.username is not None:
        username = req.username.strip()
        ok, msg = validate_username(username)
        if not ok:
            return _error("USERNAME_INVALID", msg or "用户名格式不正确", "username")
        if username != db_user.username:
            if await username_exists(db, username):
                return _error("USERNAME_TAKEN", "用户名已被占用", "username")
            db_user.username = username
            token = create_token(db_user)

    if req.email is not None:
        email = req.email.strip().lower()
        ok, msg = validate_email(email)
        if not ok:
            return _error("EMAIL_INVALID", msg or "请输入有效的邮箱地址", "email")

        if email != (db_user.email or ""):
            code = (req.verification_code or "").strip()
            ok, msg = validate_verification_code(code)
            if not ok:
                return _error(
                    "VERIFICATION_CODE_INVALID",
                    msg or "请输入 4 位数字验证码",
                    "verification_code",
                )

            result = await db.execute(
                select(User).where(User.email == email, User.id != user.user_id)
            )
            if result.scalar_one_or_none():
                return _error("EMAIL_TAKEN", "该邮箱已被其他账号使用", "email")

            verified, err_code = await verify_and_consume_code(
                email, code, "bind_email", consume=True
            )
            if not verified:
                if err_code == "VERIFICATION_CODE_EXPIRED":
                    return _error(
                        "VERIFICATION_CODE_EXPIRED",
                        "验证码已过期，请重新获取",
                        "verification_code",
                    )
                return _error("VERIFICATION_CODE_INVALID", "验证码错误", "verification_code")

            db_user.email = email

    if req.username is None and req.email is None:
        return _error("NO_CHANGES", "没有可更新的内容")

    await db.flush()
    ctx = user_to_context(db_user)
    log_action("auth.profile_update", ctx.username, {})
    body = {
        "success": True,
        "message": "资料已更新",
        "user_id": ctx.user_id,
        "username": ctx.username,
        "email": db_user.email,
        "user_type": ctx.user_type,
        "membership_expires_at": (
            ctx.membership_expires_at.isoformat() if ctx.membership_expires_at else None
        ),
        "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
        "last_login_at": (
            db_user.last_login_at.isoformat() if db_user.last_login_at else None
        ),
    }
    if token:
        body["token"] = token
    return body

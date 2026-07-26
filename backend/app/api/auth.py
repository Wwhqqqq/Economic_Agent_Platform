"""Authentication API"""
from pydantic import BaseModel
from fastapi import APIRouter, Depends

from app.services.auth import authenticate, create_token, get_current_user, AUTH_ENABLED
from app.services.audit_log import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(req: LoginRequest):
    if not authenticate(req.username, req.password):
        return {"success": False, "message": "用户名或密码错误"}
    token = create_token(req.username)
    log_action("auth.login", req.username)
    return {"success": True, "token": token, "username": req.username}


@router.get("/me")
async def me(user: str = Depends(get_current_user)):
    return {"username": user, "auth_enabled": AUTH_ENABLED}

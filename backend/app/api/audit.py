"""Audit log API"""
from fastapi import APIRouter, Depends

from app.services.audit_log import read_logs
from app.schemas.user_context import UserContext
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs")
async def get_audit_logs(limit: int = 100, user: UserContext = Depends(get_current_user)):
    if user.user_id == 0:
        return {"logs": []}
    return {"logs": read_logs(limit=limit)}

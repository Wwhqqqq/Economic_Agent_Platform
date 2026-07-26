"""Audit log API"""
from fastapi import APIRouter, Depends

from app.services.audit_log import read_logs
from app.services.auth import require_admin

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs")
async def get_audit_logs(limit: int = 100, user: str = Depends(require_admin)):
    return {"logs": read_logs(limit=limit)}

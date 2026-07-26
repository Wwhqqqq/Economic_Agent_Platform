"""System status API"""
from fastapi import APIRouter

from app.services.health import get_system_status

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
async def system_status():
    return get_system_status()

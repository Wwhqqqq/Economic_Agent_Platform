"""平台目录 API — 企业级命名与元数据"""
from fastapi import APIRouter

from app.core.catalog import get_platform_catalog

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("")
async def get_catalog():
    """获取平台完整目录（执行模式、智能体档案、分类标签等）"""
    return get_platform_catalog()

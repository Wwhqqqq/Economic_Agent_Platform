"""Agent 管理 API"""
from fastapi import APIRouter

from app.agent.orchestrator import orchestrator
from app.core.expert_catalog import list_experts, list_teams, EXPERT_CATEGORIES
from app.llm.factory import LLMFactory

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents():
    """Deprecated: use GET /api/experts. Returns expert catalog for backward compatibility."""
    return {
        "experts": list_experts(),
        "teams": list_teams(),
        "categories": EXPERT_CATEGORIES,
        "agents": orchestrator.list_agents(),
    }


@router.get("/models")
async def list_models():
    """获取可用模型列表"""
    return {"providers": LLMFactory.list_providers()}

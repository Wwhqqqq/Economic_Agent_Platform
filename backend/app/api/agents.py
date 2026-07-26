"""Agent 管理 API"""
from fastapi import APIRouter

from app.agent.orchestrator import orchestrator
from app.llm.factory import LLMFactory

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents():
    """获取智能体档案列表"""
    return {
        "agents": orchestrator.list_agents(),
        "execution_modes": orchestrator.list_execution_modes(),
    }


@router.get("/models")
async def list_models():
    """获取可用模型列表"""
    return {"providers": LLMFactory.list_providers()}

"""技能管理 API"""
from fastapi import APIRouter, HTTPException

from app.agent.base import AgentConfig
from app.core.config import config as app_config
from app.models.settings import SkillExecuteRequest
from app.skills.executor import SkillExecutor
from app.skills.registry import skill_registry
from app.core.catalog import enrich_skill, CATEGORY_LABELS

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_skills(category: str = None):
    """获取所有技能"""
    if category:
        skills = skill_registry.get_by_category(category)
        return {"skills": [enrich_skill(skill.to_dict()) for skill in skills]}
    raw = skill_registry.list_all()
    return {
        "skills": [enrich_skill(skill) for skill in raw],
        "categories": [
            {"key": category_key, "label": CATEGORY_LABELS.get(category_key, category_key)}
            for category_key in skill_registry.list_categories()
        ],
        "total": skill_registry.skill_count,
        "active": skill_registry.get_active().name if skill_registry.get_active() else None,
    }


@router.post("/{skill_name}/activate")
async def activate_skill(skill_name: str):
    """激活技能"""
    skill = skill_registry.activate(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    return {"status": "activated", "skill": enrich_skill(skill.to_dict())}


@router.post("/deactivate")
async def deactivate_skill():
    """取消激活"""
    skill_registry.deactivate()
    return {"status": "deactivated"}


@router.post("/{skill_name}/execute")
async def execute_skill(skill_name: str, req: SkillExecuteRequest):
    """直接执行技能（不经过 WebSocket）"""
    skill = skill_registry.get(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    skill_registry.activate(skill_name)
    config = AgentConfig(
        session_id=req.session_id,
        provider=req.provider or app_config.agent.default_provider,
        model=req.model,
        temperature=req.temperature,
    )
    result = await SkillExecutor.execute_skill(skill, req.input, config)
    return {
        "success": result.success,
        "output": result.output,
        "tool_calls": result.tool_calls,
        "error": result.error,
    }

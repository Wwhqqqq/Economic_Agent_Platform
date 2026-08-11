"""技能管理 API"""
from fastapi import APIRouter, Depends, HTTPException

from app.agent.base import AgentConfig
from app.core.config import config as app_config
from app.models.settings import SkillExecuteRequest
from app.skills.executor import SkillExecutor
from app.skills.registry import skill_registry
from app.core.catalog import enrich_skill, CATEGORY_LABELS
from app.services.membership_gate import skill_requires_membership
from app.schemas.user_context import UserContext
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/skills", tags=["skills"])


def _skill_invocable_item(skill_dict: dict) -> dict:
    enriched = enrich_skill(skill_dict)
    name = enriched.get("name", "")
    slash = enriched.get("slash_command") or f"/{name}"
    return {
        "name": name,
        "display_name": enriched.get("display_name", name),
        "slash_command": slash,
        "description": enriched.get("description", ""),
        "category_label": enriched.get("category_label", ""),
        "user_invocable": enriched.get("user_invocable", True),
        "membership_required": skill_requires_membership(name),
        "installed": True,
    }


def _enrich_with_membership(skill_dict: dict) -> dict:
    enriched = enrich_skill(skill_dict)
    name = enriched.get("name", "")
    enriched["membership_required"] = skill_requires_membership(name)
    return enriched


@router.get("/invocable")
async def list_invocable_skills():
    """Skills available in chat slash `/` menu."""
    raw = skill_registry.list_invocable()
    return {"skills": [_skill_invocable_item(s) for s in raw]}


@router.get("")
async def list_skills(category: str = None):
    """获取所有技能"""
    if category:
        skills = skill_registry.get_by_category(category)
        return {"skills": [_enrich_with_membership(s.to_dict()) for s in skills]}
    raw = skill_registry.list_all()
    return {
        "skills": [_enrich_with_membership(skill) for skill in raw],
        "categories": [
            {"key": category_key, "label": CATEGORY_LABELS.get(category_key, category_key)}
            for category_key in skill_registry.list_categories()
        ],
        "total": skill_registry.skill_count,
    }


@router.post("/{skill_name}/execute")
async def execute_skill(
    skill_name: str,
    req: SkillExecuteRequest,
    user: UserContext = Depends(get_current_user),
):
    """直接执行技能（不经过 WebSocket）"""
    skill = skill_registry.get(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    if skill_requires_membership(skill_name) and not user.is_member:
        raise HTTPException(
            status_code=403,
            detail={"code": "MEMBERSHIP_REQUIRED", "message": "该技能需开通会员"},
        )

    config = AgentConfig(
        session_id=req.session_id,
        active_skill=skill_name,
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

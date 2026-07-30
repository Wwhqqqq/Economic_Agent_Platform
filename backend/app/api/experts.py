"""Expert Center API — user-facing experts and expert teams."""
from fastapi import APIRouter, HTTPException

from app.core.expert_catalog import (
    EXPERT_CATEGORIES,
    get_expert,
    list_experts,
    list_teams,
)

router = APIRouter(prefix="/api/experts", tags=["experts"])


@router.get("")
async def list_all_experts(category: str | None = None):
    return {
        "experts": list_experts(category),
        "teams": list_teams(category),
        "categories": EXPERT_CATEGORIES,
    }


@router.get("/{expert_id}")
async def get_expert_detail(expert_id: str):
    profile = get_expert(expert_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Expert '{expert_id}' not found")
    from app.core.expert_catalog import to_public_profile

    return {"expert": to_public_profile(profile)}

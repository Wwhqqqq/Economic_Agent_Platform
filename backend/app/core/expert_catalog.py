"""Expert / Expert Team catalog — loaded from YAML (runtime hidden from API)."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from app.core.expert_loader import (
    EXPERT_CATEGORIES,
    get_memory_policy,
    get_tool_policy,
    load_expert_profiles,
)

EXPERT_PROFILES: dict[str, dict[str, Any]] = {}
EXPERT_TEAMS: dict[str, dict[str, Any]] = {}


def reload_expert_catalog() -> None:
    global EXPERT_PROFILES, EXPERT_TEAMS
    profiles, teams = load_expert_profiles()
    EXPERT_PROFILES = profiles
    EXPERT_TEAMS = teams
    print(f"[Experts] Loaded {len(profiles)} experts, {len(teams)} teams from YAML")


reload_expert_catalog()


def _all_profiles() -> dict[str, dict[str, Any]]:
    return {**EXPERT_PROFILES, **EXPERT_TEAMS}


def to_public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return _public_profile(profile)


def get_expert(expert_id: str) -> Optional[dict[str, Any]]:
    return _all_profiles().get(expert_id)


def get_expert_runtime(expert_id: str) -> Optional[dict[str, Any]]:
    profile = get_expert(expert_id)
    if not profile:
        return None
    return profile.get("runtime") or {}


def _public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(profile)
    data.pop("system_prompt", None)
    data.pop("runtime", None)
    data.pop("enabled", None)
    data.pop("version", None)
    return data


def list_experts(category: Optional[str] = None) -> list[dict[str, Any]]:
    items = [_public_profile(p) for p in EXPERT_PROFILES.values() if p.get("enabled", True)]
    if category:
        items = [p for p in items if p.get("category") == category]
    return items


def list_teams(category: Optional[str] = None) -> list[dict[str, Any]]:
    items = [_public_profile(p) for p in EXPERT_TEAMS.values() if p.get("enabled", True)]
    if category:
        items = [p for p in items if p.get("category") == category]
    return items


def resolve_expert_context(
    expert_id: Optional[str],
    skill_override: Optional[str] = None,
    mode_override: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve mode, skill, and expert system prompt for orchestration."""
    if not expert_id:
        return {
            "mode": mode_override or "adaptive",
            "skill": skill_override,
            "system_prompt": None,
            "expert_name": None,
            "memory_policy": {},
            "tool_policy": {},
        }

    profile = get_expert(expert_id)
    if not profile:
        return {
            "mode": mode_override or "adaptive",
            "skill": skill_override,
            "system_prompt": None,
            "expert_name": None,
            "memory_policy": {},
            "tool_policy": {},
        }

    runtime = profile.get("runtime") or {}
    if mode_override and mode_override != "adaptive":
        mode = mode_override
    elif runtime.get("mode"):
        mode = runtime.get("mode")
    else:
        mode = mode_override or "adaptive"

    skill = skill_override if skill_override is not None else runtime.get("default_skill")
    return {
        "mode": mode,
        "skill": skill,
        "system_prompt": profile.get("system_prompt"),
        "expert_name": profile.get("name"),
        "memory_policy": get_memory_policy(runtime.get("memory_policy")),
        "tool_policy": get_tool_policy(runtime.get("tool_policy")),
        "engine": runtime.get("engine"),
        "team_class": runtime.get("team_class"),
        "protocol": runtime.get("protocol"),
    }

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

import yaml

EXPERTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "experts")

EXPERT_CATEGORIES = [
    {"key": "finance", "label": "财务与审计"},
]

_POLICY_CACHE: dict[str, dict] = {}


def _experts_dir() -> Path:
    return Path(EXPERTS_ROOT)


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_policy(kind: str, policy_id: str) -> dict:
    cache_key = f"{kind}:{policy_id}"
    if cache_key in _POLICY_CACHE:
        return _POLICY_CACHE[cache_key]
    path = _experts_dir() / "_policies" / kind / f"{policy_id}.yaml"
    data = _load_yaml(path) if path.is_file() else {}
    _POLICY_CACHE[cache_key] = data
    return data


def _compose_system_prompt(data: dict) -> str:
    prompts = data.get("prompts") or {}
    parts: list[str] = []
    persona = (prompts.get("persona") or "").strip()
    if persona:
        parts.append(persona)
    constraints = prompts.get("constraints") or []
    if constraints:
        parts.append("## Constraints")
        parts.extend(f"- {c}" for c in constraints)
    return "\n\n".join(parts)


def _normalize_profile(data: dict) -> dict[str, Any]:
    display = data.get("display") or {}
    runtime = data.get("runtime") or {}
    expert_id = data["id"]
    profile_type = data.get("type", "expert")

    default_mode = runtime.get("default_mode")
    if not default_mode:
        engine = runtime.get("engine", "")
        mode_map = {
            "plan_execute": "task_orchestration",
            "react": "reasoning_action",
            "team_protocol": "collaborative_decision",
        }
        default_mode = mode_map.get(engine, "adaptive")

    profile: dict[str, Any] = {
        "id": expert_id,
        "type": profile_type,
        "category": data.get("category", "finance"),
        "name": display.get("name", expert_id),
        "tagline": display.get("tagline", ""),
        "domains": display.get("domains", []),
        "equipped_skills": display.get("equipped_skills", []),
        "example_tasks": display.get("example_tasks", []),
        "system_prompt": _compose_system_prompt(data),
        "runtime": {
            "mode": default_mode,
            "engine": runtime.get("engine"),
            "default_skill": runtime.get("default_skill"),
            "team_class": runtime.get("team_class"),
            "protocol": runtime.get("protocol"),
            "tool_policy": runtime.get("tool_policy"),
            "memory_policy": runtime.get("memory_policy"),
            "max_iterations": runtime.get("max_iterations"),
            "timeout_seconds": runtime.get("timeout_seconds"),
        },
        "enabled": data.get("enabled", True),
        "version": data.get("version", "1.0.0"),
    }

    if profile_type == "expert":
        profile["title"] = display.get("title", "")
    if profile_type == "team":
        profile["members"] = display.get("members", [])
        profile["collaboration_flow"] = display.get("collaboration_flow", [])

    return profile


def load_expert_profiles(experts_dir: str | Path | None = None) -> tuple[dict[str, dict], dict[str, dict]]:
    root = Path(experts_dir) if experts_dir else _experts_dir()
    profiles: dict[str, dict] = {}
    teams: dict[str, dict] = {}
    if not root.is_dir():
        return profiles, teams

    for path in sorted(root.glob("*.yaml")):
        try:
            data = _load_yaml(path)
            if not data.get("enabled", True):
                continue
            normalized = _normalize_profile(data)
            if normalized["type"] == "team":
                teams[normalized["id"]] = normalized
            else:
                profiles[normalized["id"]] = normalized
        except Exception as exc:
            print(f"[ExpertLoader] Skip {path.name}: {exc}")
    return profiles, teams


def get_tool_policy(policy_id: str | None) -> dict:
    if not policy_id:
        return {}
    return _load_policy("tool_policies", policy_id)


def get_memory_policy(policy_id: str | None) -> dict:
    if not policy_id:
        return {}
    data = _load_policy("memory_policies", policy_id)
    return {
        "max_history": int(data.get("max_history", 10)),
        "include_knowledge": bool(data.get("include_knowledge", True)),
        "include_entities": bool(data.get("include_entities", True)),
        "include_long_term": bool(data.get("include_long_term", True)),
    }


def reload_catalog() -> tuple[dict[str, dict], dict[str, dict]]:
    return load_expert_profiles()

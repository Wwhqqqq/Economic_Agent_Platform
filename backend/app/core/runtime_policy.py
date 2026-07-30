"""Runtime policy resolver — expert/skill/mode priority (Target doc 03 §8)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.catalog import normalize_execution_mode
from app.core.expert_catalog import get_expert, resolve_expert_context
from app.core.session_context import SessionContext
from app.skills.registry import skill_registry


@dataclass
class MessageContext:
    parsed_slash_skill: Optional[str] = None
    skill: Optional[str] = None
    mode: Optional[str] = None
    expert_id: Optional[str] = None
    skill_invocation: Optional[str] = None
    clear_skill: bool = False
    clear_expert: bool = False
    user_input: str = ""


@dataclass
class ResolvedRuntime:
    mode: str
    skill: Optional[str]
    skill_invocation: Optional[str]
    system_prompt: Optional[str]
    expert_id: Optional[str]
    expert_name: Optional[str]
    engine: Optional[str] = None
    context_strategy: dict = field(default_factory=dict)
    team_class: Optional[str] = None
    team_protocol: Optional[str] = None

    def to_agent_fields(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "active_skill": self.skill,
            "skill_invocation": self.skill_invocation,
            "system_prompt": self.system_prompt,
            "expert_id": self.expert_id,
        }


def _merge_context_strategy(
    skill_name: Optional[str],
    expert_memory_policy: dict,
) -> dict:
    base = {
        "max_history": 10,
        "include_knowledge": True,
        "include_entities": True,
        "include_long_term": True,
    }
    if expert_memory_policy:
        base.update(expert_memory_policy)
    if skill_name:
        skill = skill_registry.get(skill_name)
        if skill:
            skill_strategy = skill.get_context_strategy()
            base.update(skill_strategy)
    return base


def compose_system_prompt(
    *,
    expert_prompt: Optional[str],
    skill_name: Optional[str],
) -> Optional[str]:
    parts: list[str] = []
    if skill_name:
        skill = skill_registry.get(skill_name)
        if skill:
            sp = skill.get_system_prompt().strip()
            if sp:
                parts.append(sp)
    if expert_prompt and expert_prompt.strip():
        parts.append(expert_prompt.strip())
    if not parts:
        return None
    return "\n\n".join(parts)


def resolve(session_ctx: SessionContext, message: MessageContext) -> ResolvedRuntime:
    expert_id = message.expert_id or session_ctx.active_expert_id
    if message.clear_expert:
        expert_id = None

    expert = get_expert(expert_id) if expert_id else None
    expert_ctx = resolve_expert_context(
        expert_id,
        skill_override=None,
        mode_override=None,
    )

    # --- Skill priority: slash > explicit > sticky > expert default ---
    skill = (
        message.parsed_slash_skill
        or message.skill
        or (None if message.clear_skill else session_ctx.active_skill)
        or expert_ctx.get("skill")
    )

    skill_invocation = message.skill_invocation
    if message.parsed_slash_skill:
        skill_invocation = "slash"
    elif skill and not skill_invocation:
        if message.skill:
            skill_invocation = message.skill_invocation or "explicit"
        elif session_ctx.active_skill == skill and session_ctx.skill_invocation:
            skill_invocation = session_ctx.skill_invocation
        elif expert_id and expert_ctx.get("skill") == skill:
            skill_invocation = "expert"

    # --- Mode priority: user non-adaptive > session engine > expert > adaptive ---
    if message.mode and message.mode != "adaptive":
        mode = normalize_execution_mode(message.mode)
    elif session_ctx.engine:
        engine_mode_map = {
            "plan_execute": "task_orchestration",
            "react": "reasoning_action",
            "team_protocol": "collaborative_decision",
        }
        mode = engine_mode_map.get(session_ctx.engine, session_ctx.engine)
    elif expert:
        mode = normalize_execution_mode(expert_ctx.get("mode") or "adaptive")
    else:
        mode = "adaptive"

    system_prompt = compose_system_prompt(
        expert_prompt=expert_ctx.get("system_prompt") if expert_id else None,
        skill_name=skill,
    )

    context_strategy = _merge_context_strategy(
        skill,
        expert_ctx.get("memory_policy") or {},
    )

    return ResolvedRuntime(
        mode=mode,
        skill=skill,
        skill_invocation=skill_invocation,
        system_prompt=system_prompt,
        expert_id=expert_id,
        expert_name=expert_ctx.get("expert_name") if expert_id else None,
        engine=expert_ctx.get("engine") if expert_id else session_ctx.engine,
        context_strategy=context_strategy,
        team_class=expert_ctx.get("team_class"),
        team_protocol=expert_ctx.get("protocol"),
    )


def apply_to_session(session_ctx: SessionContext, resolved: ResolvedRuntime) -> None:
    session_ctx.active_expert_id = resolved.expert_id
    session_ctx.engine = resolved.engine
    session_ctx.active_skill = resolved.skill
    session_ctx.skill_invocation = resolved.skill_invocation
    session_ctx.context_strategy = resolved.context_strategy

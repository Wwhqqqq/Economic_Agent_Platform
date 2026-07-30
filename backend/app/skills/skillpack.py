from __future__ import annotations

from typing import TYPE_CHECKING

from app.skills.base import BaseSkill, SkillResult
from app.skills.loader import SkillManifest, load_system_prompt

if TYPE_CHECKING:
    from app.agent.base import AgentConfig


class SkillPackSkill(BaseSkill):
    """Runtime skill backed by a SKILL.md manifest directory."""

    def __init__(self, manifest: SkillManifest):
        self._manifest = manifest
        self._system_prompt_cache: str | None = None

    @property
    def manifest(self) -> SkillManifest:
        return self._manifest

    @property
    def name(self) -> str:
        return self._manifest.name

    @property
    def description(self) -> str:
        return self._manifest.description

    @property
    def category(self) -> str:
        return self._manifest.category

    @property
    def icon(self) -> str:
        return self._manifest.icon

    def get_system_prompt(self) -> str:
        if self._system_prompt_cache is None:
            self._system_prompt_cache = load_system_prompt(self._manifest)
        return self._system_prompt_cache

    def get_required_tools(self) -> list[str]:
        return list(self._manifest.required_tools)

    def get_context_strategy(self) -> dict:
        return dict(self._manifest.context_strategy)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "display_name": self._manifest.display_name,
            "category_label": self._manifest.category_label,
            "slash_command": self._manifest.slash,
            "user_invocable": self._manifest.user_invocable,
            "installed": True,
            "version": self._manifest.version,
        })
        return data

    async def execute(
        self,
        user_input: str,
        config: "AgentConfig | None" = None,
        **kwargs,
    ) -> SkillResult:
        from app.agent.base import AgentConfig
        from app.skills.executor import SkillExecutor

        cfg = config or AgentConfig()
        if not cfg.active_skill:
            cfg.active_skill = self.name
        return await SkillExecutor.execute_skill(self, user_input, cfg)

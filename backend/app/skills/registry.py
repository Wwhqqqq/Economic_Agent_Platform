"""
技能注册中心 — 动态技能管理

支持 SKILL.md 目录扫描与运行时注册
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from app.skills.base import BaseSkill
from app.skills.loader import discover_skillpacks
from app.tools.registry import tool_registry

SKILLS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skills")


class SkillRegistry:
    """技能注册中心（单例模式）"""

    _instance: Optional["SkillRegistry"] = None

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}
        self._on_skill_change: list[Callable] = []

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill
        print(f"[Skills] Registered: {skill.name} ({skill.category})")

    def unregister(self, name: str) -> bool:
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def _validate_tools(self, skill: BaseSkill) -> list[str]:
        missing = []
        for tool_name in skill.get_required_tools():
            if not tool_registry.get(tool_name):
                missing.append(tool_name)
        return missing

    def list_all(self) -> list[dict]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "icon": skill.icon,
                "required_tools": skill.get_required_tools(),
                "context_strategy": skill.get_context_strategy(),
                **(
                    skill.to_dict()
                    if hasattr(skill, "to_dict")
                    else {}
                ),
            }
            for skill in self._skills.values()
        ]

    def list_invocable(self) -> list[dict]:
        items = []
        for skill in self._skills.values():
            data = skill.to_dict() if hasattr(skill, "to_dict") else {
                "name": skill.name,
                "description": skill.description,
            }
            user_invocable = data.get("user_invocable", True)
            if user_invocable is False:
                continue
            items.append(data)
        return items

    def list_categories(self) -> list[str]:
        return list(set(skill.category for skill in self._skills.values()))

    def get_by_category(self, category: str) -> list[BaseSkill]:
        return [skill for skill in self._skills.values() if skill.category == category]

    def on_change(self, callback: Callable) -> None:
        self._on_skill_change.append(callback)

    def load_from_directory(self, skills_root: str | None = None) -> int:
        from app.skills.skillpack import SkillPackSkill

        root = skills_root or SKILLS_ROOT
        count = 0
        for manifest in discover_skillpacks(root):
            skill = SkillPackSkill(manifest)
            missing = self._validate_tools(skill)
            if missing:
                print(f"[Skills] Warning: missing tools for '{skill.name}': {missing}")
            self.register(skill)
            count += 1
        return count

    @property
    def skill_count(self) -> int:
        return len(self._skills)


skill_registry = SkillRegistry.get_instance()

"""
技能注册中心 — 动态技能管理

支持技能的注册、激活、工具依赖检查
"""
from typing import Optional, Callable

from app.skills.base import BaseSkill
from app.tools.registry import tool_registry


class SkillRegistry:
    """技能注册中心（单例模式）"""

    _instance: Optional["SkillRegistry"] = None

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}
        self._active_skill: Optional[str] = None
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
            if self._active_skill == name:
                self._active_skill = None
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

    def activate(self, name: str) -> Optional[BaseSkill]:
        skill = self._skills.get(name)
        if skill:
            missing = self._validate_tools(skill)
            if missing:
                print(f"[Skills] Warning: missing tools for '{name}': {missing}")
            self._active_skill = name
            for callback in self._on_skill_change:
                callback(name)
            print(f"[Skills] Activated: {name}")
        return skill

    def deactivate(self) -> None:
        self._active_skill = None

    def get_active(self) -> Optional[BaseSkill]:
        if self._active_skill:
            return self._skills.get(self._active_skill)
        return None

    def list_all(self) -> list[dict]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "icon": skill.icon,
                "required_tools": skill.get_required_tools(),
                "context_strategy": skill.get_context_strategy(),
                "active": skill.name == self._active_skill,
            }
            for skill in self._skills.values()
        ]

    def list_categories(self) -> list[str]:
        return list(set(skill.category for skill in self._skills.values()))

    def get_by_category(self, category: str) -> list[BaseSkill]:
        return [skill for skill in self._skills.values() if skill.category == category]

    def on_change(self, callback: Callable) -> None:
        self._on_skill_change.append(callback)

    @property
    def skill_count(self) -> int:
        return len(self._skills)


skill_registry = SkillRegistry.get_instance()

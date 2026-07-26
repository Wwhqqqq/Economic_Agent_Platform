"""
技能基类 — 高级能力抽象

技能 = 多个工具的编排 + 专用Prompt策略 + 上下文策略
一个技能可以调用多个工具，形成端到端的复杂任务解决方案
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    output: str
    tool_calls: list[dict] = field(default_factory=list)
    error: Optional[str] = None


class BaseSkill(ABC):
    """
    技能抽象基类

    技能是比工具更高级的抽象：
    - 工具 = 原子操作（搜索、计算、读文件...）
    - 技能 = 复合能力（财务审计 = 三大报表工具 + 比率分析 + 结论生成）
    """

    name: str = ""
    description: str = ""
    category: str = "general"
    icon: str = "🔧"

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取技能专用 System Prompt"""
        ...

    @abstractmethod
    def get_required_tools(self) -> list[str]:
        """获取技能依赖的工具名称列表"""
        ...

    @abstractmethod
    async def execute(self, user_input: str, **kwargs) -> SkillResult:
        """执行技能（包含工具编排逻辑）"""
        ...

    def get_context_strategy(self) -> dict:
        """
        获取上下文策略配置

        Returns:
            {
                "max_history": int,
                "include_knowledge": bool,  # 是否注入知识库 RAG
                "include_entities": bool,     # 是否注入知识图谱
                "include_long_term": bool,    # 是否注入跨会话长期记忆
            }
        """
        return {
            "max_history": 20,
            "include_knowledge": True,
            "include_entities": True,
            "include_long_term": True,
        }

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "required_tools": self.get_required_tools(),
        }

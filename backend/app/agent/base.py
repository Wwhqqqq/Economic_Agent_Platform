"""
Agent 基类 — 统一的 Agent 抽象层

定义所有 Agent 的通用接口和事件系统
支持流式输出和中间步骤追踪
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator, Any
from enum import Enum


class AgentEventType(str, Enum):
    """Agent 事件类型"""
    START = "start"
    THINKING = "thinking"          # Agent 正在思考
    TOOL_CALL = "tool_call"        # 调用工具
    TOOL_RESULT = "tool_result"    # 工具返回结果
    REASONING = "reasoning"        # 推理步骤
    INTERMEDIATE = "intermediate"  # 中间结果
    STEP = "step"                  # 结构化步骤（Plan/辩论/技能流水线）
    CITATION = "citation"          # RAG 知识引用
    FINAL = "final"                # 最终输出
    ERROR = "error"
    DONE = "done"


@dataclass
class AgentEvent:
    """Agent 执行过程中的事件"""
    type: AgentEventType
    data: Any = None
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Agent 执行完成后的响应"""
    output: str
    events: list[AgentEvent] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    intermediate_steps: list[tuple] = field(default_factory=list)
    tokens_used: int = 0
    execution_time_ms: float = 0


@dataclass
class AgentConfig:
    """Agent 运行配置"""
    provider: str = "deepseek"
    model: str = None
    temperature: float = 0.7
    max_iterations: int = 10
    session_id: str = "default"
    user_id: int | None = None
    user_type: str = "regular"
    active_skill: str | None = None
    expert_id: str | None = None
    skill_invocation: str | None = None
    streaming: bool = True
    system_prompt: str = None


class BaseAgent(ABC):
    """
    Agent 抽象基类

    所有 Agent 实现都继承此类，提供统一的执行接口。
    完美集成 LCEL Runnable 表达式。
    """

    name: str = "base_agent"
    description: str = "Base agent"

    @abstractmethod
    async def invoke(
        self, user_input: str, config: AgentConfig = None
    ) -> AgentResponse:
        """
        同步执行 Agent（返回完整结果）

        Args:
            user_input: 用户输入
            config: Agent 配置

        Returns:
            AgentResponse: 包含输出、中间步骤等
        """
        ...

    @abstractmethod
    async def stream(
        self, user_input: str, config: AgentConfig = None
    ) -> AsyncIterator[AgentEvent]:
        """
        流式执行 Agent（实时返回事件）

        Args:
            user_input: 用户输入
            config: Agent 配置

        Yields:
            AgentEvent: 流式事件
        """
        ...

    @abstractmethod
    async def to_runnable(self):
        """转为 LangChain Runnable（用于 LCEL 编排）"""
        ...

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
        }

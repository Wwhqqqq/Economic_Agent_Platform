"""
多Agent团队基类
提供团队编排的通用框架
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.agent.base import AgentConfig, AgentEvent


class MultiAgentTeam(ABC):
    """多Agent团队抽象基类"""

    name: str = "multi_agent_team"
    description: str = "A team of collaborative agents"

    @abstractmethod
    async def invoke(
        self, user_input: str, config: AgentConfig = None
    ):
        """同步执行团队任务"""
        ...

    @abstractmethod
    async def stream(
        self, user_input: str, config: AgentConfig = None
    ) -> AsyncIterator[AgentEvent]:
        """流式执行团队任务"""
        ...

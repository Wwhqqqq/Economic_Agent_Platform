r"""
ReAct Agent — 推理-行动循环（Thought → Action → Observation → Final Answer）

通过共享 runtime 模块实现完整的工具调用与流式事件推送。
"""
from typing import AsyncIterator

from langchain_core.runnables import Runnable, RunnableLambda

from app.agent.base import BaseAgent, AgentConfig, AgentEvent, AgentResponse
from app.agent.runtime import (
    collect_react_response,
    normalize_agent_config,
    run_react_loop,
)


class ReActAgent(BaseAgent):
    """ReAct (Reasoning + Acting) Agent"""

    name = "react_agent"
    description = "ReAct Agent with reasoning-action loop, tool integration, and streaming"

    async def invoke(
        self,
        user_input: str,
        config: AgentConfig = None,
        *,
        persist_memory: bool = True,
    ) -> AgentResponse:
        config = normalize_agent_config(config)
        return await collect_react_response(
            user_input,
            config,
            persist_memory=persist_memory,
        )

    async def stream(
        self, user_input: str, config: AgentConfig = None
    ) -> AsyncIterator[AgentEvent]:
        """
        流式执行 Agent — 推送 THINKING / TOOL_CALL / TOOL_RESULT / REASONING / FINAL

        注意：START 事件由 AgentOrchestrator 统一发送，此处不再重复。
        """
        config = normalize_agent_config(config)
        async for event in run_react_loop(
            user_input,
            config,
            persist_memory=True,
        ):
            yield event

    async def to_runnable(self) -> Runnable:
        async def _run(inputs: dict):
            user_input = inputs.get("input", inputs.get("query", ""))
            session_id = inputs.get("session_id", "default")
            config = normalize_agent_config(
                AgentConfig(session_id=session_id)
            )
            response = await self.invoke(user_input, config)
            return {
                "output": response.output,
                "tool_calls": response.tool_calls,
                "execution_time_ms": response.execution_time_ms,
            }

        return RunnableLambda(_run)

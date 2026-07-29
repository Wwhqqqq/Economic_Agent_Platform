"""
Agent 调度编排器 — 企业级统一入口

负责：
1. 执行模式规范化与智能路由
2. Agent 生命周期管理（固定 DeepSeek + 技能 Prompt 注入）
3. 流式事件输出
"""
from typing import Optional, AsyncIterator

from app.agent.base import (
    BaseAgent,
    AgentConfig,
    AgentEvent,
    AgentEventType,
    AgentResponse,
)
from app.agent.react_agent import ReActAgent
from app.agent.plan_execute import PlanExecuteAgent
from app.agent.runtime import normalize_agent_config, resolve_system_prompt
from app.core.catalog import (
    normalize_execution_mode,
    resolve_legacy_mode,
    AGENT_PROFILES,
    EXECUTION_MODES,
)
from app.core.connection_context import get_active_skill_name
from app.skills.registry import skill_registry


class AgentOrchestrator:
    """Agent 调度编排器（单例）"""

    _instance: Optional["AgentOrchestrator"] = None

    def __init__(self):
        self._react_agent = ReActAgent()
        self._plan_execute_agent = PlanExecuteAgent()

    @classmethod
    def get_instance(cls) -> "AgentOrchestrator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _prepare_config(self, config: AgentConfig | None) -> AgentConfig:
        """规范化 Agent 配置（固定 DeepSeek）。"""
        return normalize_agent_config(config)

    def _select_mode(self, user_input: str, mode: str) -> str:
        """
        智能路由：返回规范 execution_mode key
        adaptive / reasoning_action / task_orchestration / collaborative_decision
        """
        canonical = normalize_execution_mode(mode)
        if canonical != "adaptive":
            return canonical

        complex_keywords = ["分析", "审计", "评估", "报告", "计划", "对比", "审核", "尽调"]
        debate_keywords = ["辩论", "讨论", "评审", "多方", "角度", "委员会"]

        if any(kw in user_input for kw in debate_keywords):
            return "collaborative_decision"
        if any(kw in user_input for kw in complex_keywords):
            return "task_orchestration"
        return "reasoning_action"

    def _get_agent(self, canonical_mode: str) -> BaseAgent:
        legacy = resolve_legacy_mode(canonical_mode)
        if legacy == "multi_agent":
            from app.multi_agent.accounting.debate_team import AccountingDebateTeam
            return AccountingDebateTeam()
        if legacy == "plan_execute":
            return self._plan_execute_agent
        return self._react_agent

    async def invoke(
        self,
        user_input: str,
        config: AgentConfig = None,
        mode: str = "adaptive",
    ) -> AgentResponse:
        config = self._prepare_config(config)
        selected = self._select_mode(user_input, mode)
        agent = self._get_agent(selected)
        return await agent.invoke(user_input, config)

    async def stream(
        self,
        user_input: str,
        config: AgentConfig = None,
        mode: str = "adaptive",
    ) -> AsyncIterator[AgentEvent]:
        config = self._prepare_config(config)
        selected = self._select_mode(user_input, mode)

        mode_meta = EXECUTION_MODES.get(selected, {})
        skill_name = config.active_skill or get_active_skill_name()
        active_skill = skill_registry.get(skill_name) if skill_name else None
        yield AgentEvent(
            type=AgentEventType.START,
            data={
                "input": user_input,
                "execution_mode": selected,
                "execution_mode_name": mode_meta.get("name", selected),
                "session_id": config.session_id,
                "provider": config.provider,
                "active_skill": active_skill.name if active_skill else None,
            },
        )

        agent = self._get_agent(selected)
        async for event in agent.stream(user_input, config):
            if event.type == AgentEventType.START:
                continue
            yield event

    def list_agents(self) -> list[dict]:
        """返回企业级智能体档案"""
        return list(AGENT_PROFILES.values())

    def list_execution_modes(self) -> list[dict]:
        return list(EXECUTION_MODES.values())


orchestrator = AgentOrchestrator.get_instance()

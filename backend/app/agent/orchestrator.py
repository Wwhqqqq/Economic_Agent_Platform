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
from app.schemas.user_context import UserContext


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

    def _select_mode(self, user_input: str, mode: str, user: UserContext | None = None) -> str:
        """
        智能路由：返回规范 execution_mode key
        adaptive / reasoning_action / task_orchestration / collaborative_decision
        """
        canonical = normalize_execution_mode(mode)
        if canonical != "adaptive":
            return canonical

        # 普通用户 Auto 固定走 ReAct，不做关键词升级
        if user is not None and not user.is_member:
            return "reasoning_action"

        complex_keywords = ["分析", "审计", "评估", "报告", "计划", "对比", "审核", "尽调"]
        debate_keywords = ["辩论", "讨论", "评审", "多方", "角度", "委员会"]

        if any(kw in user_input for kw in debate_keywords):
            return "collaborative_decision"
        if any(kw in user_input for kw in complex_keywords):
            return "task_orchestration"
        return "reasoning_action"

    def _get_agent(self, canonical_mode: str, config: AgentConfig | None = None):
        if config and (config.engine == "team_protocol" or config.team_protocol):
            from app.orchestration.team_protocol import TeamProtocolEngine
            return TeamProtocolEngine()
        legacy = resolve_legacy_mode(canonical_mode)
        if legacy == "multi_agent":
            if config and config.team_protocol:
                from app.orchestration.team_protocol import TeamProtocolEngine
                return TeamProtocolEngine()
            from app.multi_agent.accounting.debate_team import AccountingDebateTeam
            return AccountingDebateTeam()
        if legacy == "plan_execute":
            return self._plan_execute_agent
        return self._react_agent

    def _resolve_mode(self, user_input: str, mode: str, config: AgentConfig, user: UserContext | None = None) -> str:
        if config.engine == "team_protocol" or config.team_protocol:
            return "collaborative_decision"
        return self._select_mode(user_input, mode, user)

    async def invoke(
        self,
        user_input: str,
        config: AgentConfig = None,
        mode: str = "adaptive",
        user: UserContext | None = None,
    ) -> AgentResponse:
        config = self._prepare_config(config)
        if user is None and config and config.user_type:
            user = UserContext(
                user_id=config.user_id or 0,
                username="",
                user_type=config.user_type,
            )
        selected = self._resolve_mode(user_input, mode, config, user)
        agent = self._get_agent(selected, config)
        if agent.__class__.__name__ == "TeamProtocolEngine":
            return await agent.invoke(
                user_input, config, protocol_id=config.team_protocol or "debate_v1"
            )
        return await agent.invoke(user_input, config)

    async def stream(
        self,
        user_input: str,
        config: AgentConfig = None,
        mode: str = "adaptive",
        user: UserContext | None = None,
    ) -> AsyncIterator[AgentEvent]:
        config = self._prepare_config(config)
        if user is None and config and config.user_type:
            user = UserContext(
                user_id=config.user_id or 0,
                username="",
                user_type=config.user_type,
                membership_expires_at=getattr(config, "membership_expires_at", None),
            )
        selected = self._resolve_mode(user_input, mode, config, user)

        mode_meta = EXECUTION_MODES.get(selected, {})
        skill_name = config.active_skill
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
                "expert_id": config.expert_id,
                "team_protocol": config.team_protocol,
            },
        )

        agent = self._get_agent(selected, config)
        if agent.__class__.__name__ == "TeamProtocolEngine":
            async for event in agent.stream(
                user_input, config, protocol_id=config.team_protocol or "debate_v1"
            ):
                if event.type == AgentEventType.START:
                    continue
                yield event
            return

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

"""
会计学 Multi-Agent 辩论团队

三个角色:
1. 分析师 (Financial Analyst) — 正方
2. 质疑者 (Audit Skeptic) — 反方
3. 裁判 (Chief Judge) — 综合裁决
"""
import re
from typing import AsyncIterator

from langchain_core.messages import HumanMessage

from app.agent.base import (
    AgentConfig,
    AgentEvent,
    AgentEventType,
    AgentResponse,
)
from app.agent.runtime import (
    collect_prompt_tool_response,
    create_llm,
    message_content,
    normalize_agent_config,
    run_prompt_tool_loop,
    stream_llm_text_events,
    TextStreamComplete,
)
from app.core.config import config as app_config
from app.memory.manager import memory_manager
from app.multi_agent.team import MultiAgentTeam
from app.multi_agent.debate import DebateRound, DebateResult
from app.tools.registry import tool_registry

ROLE_MAX_TOOL_ITERATIONS = 5

ANALYST_SYSTEM_PROMPT = """You are a **Senior Financial Analyst** with 15 years of experience at a Big Four accounting firm.

## Your Role
You are the PROPOSER in a financial analysis debate. Your job is to:
1. Analyze financial data rigorously using available tools
2. Present well-supported conclusions based on evidence
3. Defend your analysis against skeptical challenges
4. Acknowledge limitations honestly when appropriate

## Methodology
- Start with balance sheet verification (A = L + E)
- Compute key financial ratios using available tools
- Perform DuPont analysis to understand ROE drivers
- Analyze cash flow quality
- Provide clear, numerically-supported arguments

Available tools: balance_sheet_analyzer, income_statement_analyzer, cash_flow_analyzer,
financial_ratio_calculator, dupont_analysis, calculator"""


SKEPTIC_SYSTEM_PROMPT = """You are an **Audit Partner & Professional Skeptic** with expertise in forensic accounting.

## Your Role
You are the OPPONENT in a financial analysis debate. Your job is to:
1. Challenge the Analyst's conclusions aggressively but professionally
2. Identify hidden risks, aggressive accounting practices, and red flags
3. Question assumptions and methodology
4. Propose alternative interpretations of the data

Use the same financial analysis tools to verify claims when needed."""


JUDGE_SYSTEM_PROMPT = """You are the **Chief Investment Judge** with 25 years of experience in capital markets.

## Your Role
You are the JUDGE in a financial analysis debate. Your job is to:
1. Listen to both the Analyst and the Skeptic
2. Evaluate which arguments are most compelling
3. Identify areas of consensus and remaining disagreements
4. Deliver a final, balanced verdict with clear reasoning
"""


class AccountingDebateTeam(MultiAgentTeam):
    """财务评审委员会 — 三角色多轮辩论 + 工具验证"""

    name = "financial_review_board"
    description = "财务评审委员会：分析师、质疑官、裁决官多轮结构化辩论"

    def __init__(self, max_rounds: int = None):
        self.max_rounds = max_rounds or app_config.agent.debate_max_rounds
        self._debate_tools = tool_registry.to_langchain_tools(
            categories=["accounting", "general", "web"]
        )
        self._judge_llm = create_llm(AgentConfig(temperature=0.3))

    async def _run_role(
        self,
        prompt: str,
        *,
        temperature: float,
    ) -> tuple[str, list[dict]]:
        return await collect_prompt_tool_response(
            prompt,
            temperature=temperature,
            tools=self._debate_tools,
            max_iterations=ROLE_MAX_TOOL_ITERATIONS,
        )

    async def _stream_role(
        self,
        prompt: str,
        *,
        role: str,
        round_num: int,
        temperature: float,
        config: AgentConfig,
    ) -> AsyncIterator[AgentEvent | tuple[str, list[dict]]]:
        output = ""
        tool_calls: list[dict] = []
        async for event in run_prompt_tool_loop(
            prompt,
            temperature=temperature,
            tools=self._debate_tools,
            max_iterations=ROLE_MAX_TOOL_ITERATIONS,
            config=config,
        ):
            if event.type == AgentEventType.FINAL:
                output = event.data.get("output", "")
                tool_calls = event.data.get("tool_calls", [])
                continue
            event.metadata.update({"role": role, "round": round_num})
            yield event
        yield (output, tool_calls)

    async def _execute_round(
        self,
        round_num: int,
        topic: str,
        previous_context: str,
        config: AgentConfig,
    ) -> tuple[DebateRound, list[dict]]:
        debate_round = DebateRound(
            round_number=round_num,
            proposer_argument="",
            opponent_argument="",
        )
        all_tool_calls: list[dict] = []

        analyst_prompt = self._build_analyst_prompt(topic, previous_context, round_num)
        analyst_output, analyst_tools = await self._run_role(
            analyst_prompt,
            temperature=0.4,
        )
        debate_round.proposer_argument = analyst_output
        all_tool_calls.extend(analyst_tools)

        skeptic_prompt = self._build_skeptic_prompt(
            topic, debate_round.proposer_argument, round_num
        )
        skeptic_output, skeptic_tools = await self._run_role(
            skeptic_prompt,
            temperature=0.5,
        )
        debate_round.opponent_argument = skeptic_output
        all_tool_calls.extend(skeptic_tools)

        judge_prompt = self._build_judge_summary_prompt(
            topic,
            debate_round.proposer_argument,
            debate_round.opponent_argument,
            round_num,
        )
        judge_response = await self._judge_llm.ainvoke([HumanMessage(content=judge_prompt)])
        debate_round.judge_summary = message_content(judge_response)

        return debate_round, all_tool_calls

    async def _final_judgment(
        self, topic: str, result: DebateResult, config: AgentConfig
    ) -> tuple[str, dict]:
        rounds_text = "\n\n".join(
            f"### Round {r.round_number}\n"
            f"**Analyst**: {r.proposer_argument[:500]}...\n"
            f"**Skeptic**: {r.opponent_argument[:500]}...\n"
            f"**Judge**: {r.judge_summary}"
            for r in result.rounds
        )

        final_prompt = f"""{JUDGE_SYSTEM_PROMPT}

Original Topic: {topic}

Debate History:
{rounds_text}

Deliver your final judgment in markdown with sections:
## Final Verdict
## Key Findings
## Risks to Monitor
## Consensus Points
## Recommended Next Steps
"""

        response = await self._judge_llm.ainvoke([HumanMessage(content=final_prompt)])
        verdict = message_content(response)
        structured = self._parse_verdict_sections(verdict)
        result.final_verdict = verdict
        result.key_findings = structured.get("key_findings", [])
        result.risks_identified = structured.get("risks_identified", [])
        result.consensus_points = structured.get("consensus_points", [])
        return verdict, structured

    def _parse_verdict_sections(self, verdict: str) -> dict:
        """从终审 markdown 中提取结构化要点。"""
        sections = {
            "key_findings": [],
            "risks_identified": [],
            "consensus_points": [],
        }
        current = None
        for line in verdict.splitlines():
            header = line.strip().lower()
            if header.startswith("## key findings"):
                current = "key_findings"
                continue
            if header.startswith("## risks to monitor"):
                current = "risks_identified"
                continue
            if header.startswith("## consensus points"):
                current = "consensus_points"
                continue
            if line.strip().startswith("- ") and current in sections:
                sections[current].append(line.strip()[2:].strip())
        return sections

    async def invoke(
        self, user_input: str, config: AgentConfig = None
    ) -> AgentResponse:
        config = normalize_agent_config(config)
        result = DebateResult()
        previous_context = ""
        all_tool_calls: list[dict] = []

        for round_num in range(1, self.max_rounds + 1):
            debate_round, round_tools = await self._execute_round(
                round_num, user_input, previous_context, config
            )
            result.rounds.append(debate_round)
            all_tool_calls.extend(round_tools)
            previous_context = debate_round.judge_summary

        verdict, _ = await self._final_judgment(user_input, result, config)
        await memory_manager.save_context(config.session_id, user_input, verdict, user_id=config.user_id)

        return AgentResponse(
            output=verdict,
            tool_calls=all_tool_calls,
        )

    async def stream(
        self, user_input: str, config: AgentConfig = None
    ) -> AsyncIterator[AgentEvent]:
        config = normalize_agent_config(config)
        result = DebateResult()
        previous_context = ""
        all_tool_calls: list[dict] = []

        try:
            for round_num in range(1, self.max_rounds + 1):
                yield AgentEvent(
                    type=AgentEventType.INTERMEDIATE,
                    data={
                        "phase": "debate_round",
                        "round": round_num,
                        "total_rounds": self.max_rounds,
                    },
                )

                debate_round = DebateRound(
                    round_number=round_num,
                    proposer_argument="",
                    opponent_argument="",
                )

                analyst_prompt = self._build_analyst_prompt(
                    user_input, previous_context, round_num
                )
                yield AgentEvent(
                    type=AgentEventType.THINKING,
                    data={
                        "role": "analyst",
                        "round": round_num,
                        "message": "分析师正在分析并调用工具...",
                    },
                )
                async for item in self._stream_role(
                    analyst_prompt,
                    role="analyst",
                    round_num=round_num,
                    temperature=0.4,
                    config=config,
                ):
                    if isinstance(item, tuple):
                        debate_round.proposer_argument, tools = item
                        all_tool_calls.extend(tools)
                    else:
                        yield item

                skeptic_prompt = self._build_skeptic_prompt(
                    user_input, debate_round.proposer_argument, round_num
                )
                yield AgentEvent(
                    type=AgentEventType.THINKING,
                    data={
                        "role": "skeptic",
                        "round": round_num,
                        "message": "质疑官正在挑战并验证观点...",
                    },
                )
                async for item in self._stream_role(
                    skeptic_prompt,
                    role="skeptic",
                    round_num=round_num,
                    temperature=0.5,
                    config=config,
                ):
                    if isinstance(item, tuple):
                        debate_round.opponent_argument, tools = item
                        all_tool_calls.extend(tools)
                    else:
                        yield item

                judge_prompt = self._build_judge_summary_prompt(
                    user_input,
                    debate_round.proposer_argument,
                    debate_round.opponent_argument,
                    round_num,
                )
                yield AgentEvent(
                    type=AgentEventType.THINKING,
                    data={
                        "role": "judge",
                        "round": round_num,
                        "message": "裁决官正在总结本轮...",
                    },
                )
                judge_text = ""
                async for item in stream_llm_text_events(
                    self._judge_llm,
                    [HumanMessage(content=judge_prompt)],
                    config,
                ):
                    if isinstance(item, TextStreamComplete):
                        judge_text = item.text
                    else:
                        item.metadata.update({"role": "judge", "round": round_num})
                        yield item
                debate_round.judge_summary = judge_text

                result.rounds.append(debate_round)
                previous_context = debate_round.judge_summary

            rounds_text = "\n\n".join(
                f"### Round {r.round_number}\n"
                f"**Analyst**: {r.proposer_argument[:500]}...\n"
                f"**Skeptic**: {r.opponent_argument[:500]}...\n"
                f"**Judge**: {r.judge_summary}"
                for r in result.rounds
            )
            final_prompt = f"""{JUDGE_SYSTEM_PROMPT}

Original Topic: {user_input}

Debate History:
{rounds_text}

Deliver your final judgment in markdown with sections:
## Final Verdict
## Key Findings
## Risks to Monitor
## Consensus Points
## Recommended Next Steps
"""
            verdict = ""
            async for item in stream_llm_text_events(
                self._judge_llm,
                [HumanMessage(content=final_prompt)],
                config,
            ):
                if isinstance(item, TextStreamComplete):
                    verdict = item.text
                else:
                    item.metadata.update({"role": "judge", "phase": "final"})
                    yield item

            structured = self._parse_verdict_sections(verdict)
            result.final_verdict = verdict
            result.key_findings = structured.get("key_findings", [])
            result.risks_identified = structured.get("risks_identified", [])
            result.consensus_points = structured.get("consensus_points", [])

            yield AgentEvent(
                type=AgentEventType.FINAL,
                data={
                    "output": verdict,
                    "mode": "debate_verdict",
                    "tool_calls": all_tool_calls,
                },
            )
            await memory_manager.save_context(config.session_id, user_input, verdict, user_id=config.user_id)
            yield AgentEvent(type=AgentEventType.DONE)

        except Exception as exc:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={"message": str(exc)},
            )
            yield AgentEvent(type=AgentEventType.DONE)

    def _build_analyst_prompt(
        self, topic: str, previous_context: str, round_num: int
    ) -> str:
        if round_num == 1:
            return (
                f"{ANALYST_SYSTEM_PROMPT}\n\n"
                f"Round {round_num} - Initial Analysis\n\n"
                f"Topic: {topic}\n\n"
                f"Provide a comprehensive initial analysis using all available tools. "
                f"Start with the most important findings."
            )
        return (
            f"{ANALYST_SYSTEM_PROMPT}\n\n"
            f"Round {round_num} - Defense & Refinement\n\n"
            f"Previous context:\n{previous_context}\n\n"
            f"Respond to the Skeptic's challenges. Strengthen your analysis "
            f"where possible, acknowledge valid criticisms, and refine your position."
        )

    def _build_skeptic_prompt(
        self, topic: str, analyst_argument: str, round_num: int
    ) -> str:
        return (
            f"{SKEPTIC_SYSTEM_PROMPT}\n\n"
            f"Round {round_num}\n\n"
            f"Topic: {topic}\n\n"
            f"Analyst's argument:\n{analyst_argument[:2000]}\n\n"
            f"Challenge the Analyst's analysis. Identify risks, questionable assumptions, "
            f"and areas that need more scrutiny. Use tools to verify their claims."
        )

    def _build_judge_summary_prompt(
        self,
        topic: str,
        analyst_arg: str,
        skeptic_arg: str,
        round_num: int,
    ) -> str:
        return (
            f"{JUDGE_SYSTEM_PROMPT}\n\n"
            f"Round {round_num} Summary\n\n"
            f"Topic: {topic}\n\n"
            f"Analyst's argument:\n{analyst_arg[:1500]}\n\n"
            f"Skeptic's challenge:\n{skeptic_arg[:1500]}\n\n"
            f"Summarize this round: whose arguments were stronger? "
            f"What needs more discussion in the next round?"
        )

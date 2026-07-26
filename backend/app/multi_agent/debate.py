"""
辩论范式基类 — Multi-Agent Debate 框架

实现裁判制辩论（Judge-mediated Debate）：
1. Proposer (正方): 提出观点和分析
2. Opponent (反方): 质疑和反驳
3. Judge (裁判): 综合评估，给出最终裁决

支持多轮辩论，每轮结束后由裁判总结进展。
"""
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator

from app.agent.base import AgentConfig, AgentEvent, AgentEventType


@dataclass
class DebateRound:
    """单轮辩论记录"""
    round_number: int
    proposer_argument: str
    opponent_argument: str
    judge_summary: str = ""


@dataclass
class DebateResult:
    """辩论最终结果"""
    rounds: list[DebateRound] = field(default_factory=list)
    final_verdict: str = ""
    key_findings: list[str] = field(default_factory=list)
    risks_identified: list[str] = field(default_factory=list)
    consensus_points: list[str] = field(default_factory=list)


class DebateOrchestrator:
    """
    辩论编排器基类

    子类需要实现:
    - _get_proposer_prompt(): 正方系统提示
    - _get_opponent_prompt(): 反方系统提示
    - _get_judge_prompt(): 裁判系统提示
    """

    name: str = "debate"
    max_rounds: int = 3

    def _get_proposer_prompt(self, topic: str) -> str:
        raise NotImplementedError

    def _get_opponent_prompt(self, topic: str, proposer_arg: str) -> str:
        raise NotImplementedError

    def _get_judge_prompt(
        self, topic: str, rounds: list[DebateRound]
    ) -> str:
        raise NotImplementedError

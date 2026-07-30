"""Expert / Expert Team catalog — user-facing personas (runtime hidden from API)."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

EXPERT_CATEGORIES = [
    {"key": "finance", "label": "财务与审计"},
]

# Keys only used server-side when resolving summon / chat
_RUNTIME_KEYS = ("mode", "default_skill", "team_class", "agent_profile_key")

EXPERT_PROFILES: dict[str, dict[str, Any]] = {
    "finance_reviewer": {
        "id": "finance_reviewer",
        "type": "expert",
        "category": "finance",
        "name": "财务审阅专家",
        "title": "资深 CPA · 四大会计师事务所背景",
        "tagline": "三表勾稽、比率分析、审计意见一站式输出",
        "domains": ["财务审计", "报表分析", "合规初筛"],
        "equipped_skills": [
            {"name": "financial_audit", "display_name": "财务审阅技能"},
        ],
        "example_tasks": [
            {
                "label": "资产负债表审阅",
                "prompt": "请审阅以下资产负债表，指出异常科目与流动性风险",
            },
            {
                "label": "利润表同比分析",
                "prompt": "对以下利润表做同比分析并给出审计关注点",
            },
        ],
        "system_prompt": (
            "你是资深财务审阅专家（CPA），擅长三表勾稽、财务比率分析与审计意见撰写。"
            "请基于工具计算的精确数据给出专业审阅结论，避免心算财务数字。"
        ),
        "runtime": {
            "mode": "task_orchestration",
            "default_skill": "financial_audit",
        },
    },
    "report_analyst": {
        "id": "report_analyst",
        "type": "expert",
        "category": "finance",
        "name": "报表解读专家",
        "title": "财务分析顾问 · 结构化解读报表",
        "tagline": "快速读懂报表结构、关键指标与经营信号",
        "domains": ["报表分析", "指标计算", "经营解读"],
        "equipped_skills": [],
        "example_tasks": [
            {
                "label": "现金流质量分析",
                "prompt": "请分析以下现金流量表，评估盈利质量与自由现金流",
            },
            {
                "label": "杜邦分析解读",
                "prompt": "请对以下财务数据做杜邦分析并解读 ROE 驱动因素",
            },
        ],
        "system_prompt": (
            "你是资深报表解读专家，擅长从资产负债表、利润表、现金流量表中提炼关键洞察。"
            "优先调用会计分析工具获取精确比率，再给出清晰、结构化的解读。"
        ),
        "runtime": {
            "mode": "reasoning_action",
            "default_skill": None,
        },
    },
    "document_insight": {
        "id": "document_insight",
        "type": "expert",
        "category": "finance",
        "name": "文档洞察专家",
        "title": "文档智能顾问 · 要点提取与归纳",
        "tagline": "从长文档中快速提取要点、风险与行动建议",
        "domains": ["文档分析", "要点提取", "合规阅读"],
        "equipped_skills": [
            {"name": "document_analysis", "display_name": "文档洞察技能"},
        ],
        "example_tasks": [
            {
                "label": "审计报告摘要",
                "prompt": "请阅读以下文档内容并输出结构化分析摘要",
            },
        ],
        "system_prompt": (
            "你是文档洞察专家，擅长从财务与合规类文档中提取关键信息、风险点与结论。"
        ),
        "runtime": {
            "mode": "reasoning_action",
            "default_skill": "document_analysis",
        },
    },
}

EXPERT_TEAMS: dict[str, dict[str, Any]] = {
    "finance_review_board": {
        "id": "finance_review_board",
        "type": "team",
        "category": "finance",
        "name": "财务评审委员会",
        "tagline": "分析师 · 质疑官 · 裁决官 三轮协作，输出评审结论",
        "domains": ["投资评审", "风险识别", "并购尽调"],
        "members": [
            {"role": "财务分析师", "stance": "基于数据提出分析结论与假设"},
            {"role": "审计质疑官", "stance": "挑战假设，识别会计红旗与舞弊信号"},
            {"role": "投资裁决官", "stance": "综合辩论，给出最终评审意见"},
        ],
        "collaboration_flow": [
            "分析师独立分析并引用工具结果",
            "质疑官逐条挑战分析假设",
            "裁决官形成最终评审报告",
        ],
        "equipped_skills": [],
        "example_tasks": [
            {
                "label": "多视角投资评审",
                "prompt": "请对以下公司财务数据组织一场评审委员会辩论，并给出投资意见",
            },
        ],
        "system_prompt": (
            "你是财务评审委员会协调者，将组织分析师、质疑官与裁决官完成多轮结构化评审。"
        ),
        "runtime": {
            "mode": "collaborative_decision",
            "default_skill": None,
            "team_class": "AccountingDebateTeam",
        },
    },
}


def _all_profiles() -> dict[str, dict[str, Any]]:
    return {**EXPERT_PROFILES, **EXPERT_TEAMS}


def to_public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return _public_profile(profile)


def get_expert(expert_id: str) -> Optional[dict[str, Any]]:
    return _all_profiles().get(expert_id)


def get_expert_runtime(expert_id: str) -> Optional[dict[str, Any]]:
    profile = get_expert(expert_id)
    if not profile:
        return None
    return profile.get("runtime") or {}


def _public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(profile)
    data.pop("system_prompt", None)
    data.pop("runtime", None)
    return data


def list_experts(category: Optional[str] = None) -> list[dict[str, Any]]:
    items = [_public_profile(p) for p in EXPERT_PROFILES.values()]
    if category:
        items = [p for p in items if p.get("category") == category]
    return items


def list_teams(category: Optional[str] = None) -> list[dict[str, Any]]:
    items = [_public_profile(p) for p in EXPERT_TEAMS.values()]
    if category:
        items = [p for p in items if p.get("category") == category]
    return items


def resolve_expert_context(
    expert_id: Optional[str],
    skill_override: Optional[str] = None,
    mode_override: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve mode, skill, and expert system prompt for orchestration."""
    if not expert_id:
        return {
            "mode": mode_override or "adaptive",
            "skill": skill_override,
            "system_prompt": None,
            "expert_name": None,
        }

    profile = get_expert(expert_id)
    if not profile:
        return {
            "mode": mode_override or "adaptive",
            "skill": skill_override,
            "system_prompt": None,
            "expert_name": None,
        }

    runtime = profile.get("runtime") or {}
    if mode_override and mode_override != "adaptive":
        mode = mode_override
    elif runtime.get("mode"):
        mode = runtime.get("mode")
    else:
        mode = mode_override or "adaptive"
    skill = skill_override if skill_override is not None else runtime.get("default_skill")
    return {
        "mode": mode,
        "skill": skill,
        "system_prompt": profile.get("system_prompt"),
        "expert_name": profile.get("name"),
    }

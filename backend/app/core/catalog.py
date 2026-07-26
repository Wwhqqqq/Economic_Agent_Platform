"""
企业级平台目录 — 统一命名、展示文案与能力元数据

内部标识（key）保持稳定，对外展示使用规范中文名称与业务描述。
"""
from typing import Optional

# 执行模式：旧 key -> 新 key（企业级命名）
EXECUTION_MODE_ALIASES: dict[str, str] = {
    "auto": "adaptive",
    "react": "reasoning_action",
    "plan_execute": "task_orchestration",
    "multi_agent": "collaborative_decision",
    # 新 key 自身
    "adaptive": "adaptive",
    "reasoning_action": "reasoning_action",
    "task_orchestration": "task_orchestration",
    "collaborative_decision": "collaborative_decision",
}

EXECUTION_MODES: dict[str, dict] = {
    "adaptive": {
        "key": "adaptive",
        "name": "智能路由模式",
        "short_name": "智能路由",
        "tagline": "根据任务语义自动选择最优执行引擎",
        "description": "平台内置任务理解模块，会结合用户输入与已启用技能，自动路由至推理闭环、任务编排或协同决策引擎。",
        "适用场景": ["日常问答", "混合任务", "不确定复杂度时"],
        "legacy_keys": ["auto"],
    },
    "reasoning_action": {
        "key": "reasoning_action",
        "name": "推理-行动闭环引擎",
        "short_name": "推理闭环",
        "tagline": "Thought → Action → Observation 迭代推理",
        "description": "面向单轮或多轮工具调用场景，采用推理-行动循环范式，支持流式输出与中间步骤追踪。",
        "适用场景": ["信息检索", "计算验证", "轻量分析"],
        "legacy_keys": ["react"],
    },
    "task_orchestration": {
        "key": "task_orchestration",
        "name": "任务编排引擎",
        "short_name": "任务编排",
        "tagline": "先规划、再分步执行、最后汇总",
        "description": "适用于审计、尽调、报告生成等多步骤任务。系统先生成执行计划，再逐步调用工具完成子任务并合成结论。",
        "适用场景": ["财务审计", "文档分析", "复杂报告"],
        "legacy_keys": ["plan_execute"],
    },
    "collaborative_decision": {
        "key": "collaborative_decision",
        "name": "协同决策引擎",
        "short_name": "协同决策",
        "tagline": "多角色辩论 + 裁判综合裁决",
        "description": "由分析、质疑、裁决三类角色组成评审委员会，通过多轮结构化辩论提升结论可靠性与风险覆盖度。",
        "适用场景": ["财务评审", "投资研判", "合规风险评估"],
        "legacy_keys": ["multi_agent"],
    },
}

AGENT_PROFILES: dict[str, dict] = {
    "inference_action_agent": {
        "key": "inference_action_agent",
        "legacy_keys": ["react_agent"],
        "name": "推理行动智能体",
        "role": "通用任务执行单元",
        "execution_mode": "reasoning_action",
        "description": "基于 LangGraph 状态图实现的推理-行动闭环智能体，负责工具选择、调用与结果整合。",
        "capabilities": ["工具调用", "流式推理", "会话记忆", "知识检索增强"],
    },
    "task_orchestration_agent": {
        "key": "task_orchestration_agent",
        "legacy_keys": ["plan_execute_agent"],
        "name": "任务编排智能体",
        "role": "复杂任务规划与执行",
        "execution_mode": "task_orchestration",
        "description": "将复杂目标拆解为可执行步骤，逐步调度子智能体完成，并输出结构化综合报告。",
        "capabilities": ["任务分解", "步骤追踪", "结果汇总", "失败重试"],
    },
    "financial_review_board": {
        "key": "financial_review_board",
        "legacy_keys": ["accounting_debate_team"],
        "name": "财务评审委员会",
        "role": "多智能体协同决策单元",
        "execution_mode": "collaborative_decision",
        "description": "由财务分析师、审计质疑官、投资裁决官组成，针对财务数据进行多轮辩论并形成最终评审意见。",
        "capabilities": ["多角色辩论", "风险识别", "证据交叉验证", "裁决报告"],
        "members": [
            {"role": "财务分析师", "职责": "基于数据提出分析结论"},
            {"role": "审计质疑官", "职责": "挑战假设并识别潜在风险"},
            {"role": "投资裁决官", "职责": "综合各方观点给出裁决"},
        ],
    },
}

TOOL_CATALOG: dict[str, dict] = {
    "web_search": {
        "display_name": "全网信息检索",
        "category_label": "外部情报",
        "capability_tags": ["实时检索", "公开信息"],
    },
    "calculator": {
        "display_name": "数值计算引擎",
        "category_label": "基础能力",
        "capability_tags": ["表达式求值", "函数运算"],
    },
    "file_reader": {
        "display_name": "结构化文件解析",
        "category_label": "数据接入",
        "capability_tags": ["CSV", "Excel", "PDF", "JSON"],
    },
    "code_executor": {
        "display_name": "安全代码沙箱",
        "category_label": "基础能力",
        "capability_tags": ["Python", "隔离执行"],
    },
    "datetime": {
        "display_name": "时间日期服务",
        "category_label": "基础能力",
        "capability_tags": ["当前时间", "日期计算"],
    },
    "balance_sheet_analyzer": {
        "display_name": "资产负债表分析器",
        "category_label": "财务分析",
        "capability_tags": ["结构分析", "平衡验证", "偿债指标"],
    },
    "income_statement_analyzer": {
        "display_name": "利润表分析器",
        "category_label": "财务分析",
        "capability_tags": ["盈利结构", "利润率", "同比趋势"],
    },
    "cash_flow_analyzer": {
        "display_name": "现金流量表分析器",
        "category_label": "财务分析",
        "capability_tags": ["现金流结构", "自由现金流", "盈利质量"],
    },
    "financial_ratio_calculator": {
        "display_name": "财务比率计算引擎",
        "category_label": "财务分析",
        "capability_tags": ["盈利", "偿债", "营运", "成长"],
    },
    "dupont_analysis": {
        "display_name": "杜邦分析引擎",
        "category_label": "财务分析",
        "capability_tags": ["ROE分解", "驱动因素"],
    },
}

SKILL_CATALOG: dict[str, dict] = {
    "document_analysis": {
        "display_name": "文档洞察技能",
        "category_label": "文档智能",
        "workflow": ["读取文档", "结构解析", "要点提取", "对比归纳"],
    },
    "data_visualization": {
        "display_name": "数据可视化技能",
        "category_label": "数据分析",
        "workflow": ["数据解析", "图表选型", "代码生成", "洞察解读"],
    },
    "financial_audit": {
        "display_name": "财务审阅技能",
        "category_label": "财务智能",
        "workflow": ["三表校验", "比率分析", "杜邦分解", "审计报告"],
    },
}

CATEGORY_LABELS: dict[str, str] = {
    "general": "基础能力",
    "web": "外部情报",
    "file": "数据接入",
    "accounting": "财务分析",
    "document": "文档智能",
    "data": "数据分析",
}


def normalize_execution_mode(mode: Optional[str]) -> str:
    """将任意模式标识规范为企业级 key"""
    if not mode:
        return "adaptive"
    return EXECUTION_MODE_ALIASES.get(mode, "adaptive")


def resolve_legacy_mode(canonical: str) -> str:
    """将规范 key 映射回内部引擎使用的 legacy key"""
    reverse = {
        "adaptive": "auto",
        "reasoning_action": "react",
        "task_orchestration": "plan_execute",
        "collaborative_decision": "multi_agent",
    }
    return reverse.get(canonical, "auto")


def enrich_tool(tool_dict: dict) -> dict:
    meta = TOOL_CATALOG.get(tool_dict.get("name", ""), {})
    cat = tool_dict.get("category", "")
    return {
        **tool_dict,
        "display_name": meta.get("display_name", tool_dict.get("name")),
        "category_label": meta.get("category_label", CATEGORY_LABELS.get(cat, cat)),
        "capability_tags": meta.get("capability_tags", []),
    }


def enrich_skill(skill_dict: dict) -> dict:
    meta = SKILL_CATALOG.get(skill_dict.get("name", ""), {})
    cat = skill_dict.get("category", "")
    return {
        **skill_dict,
        "display_name": meta.get("display_name", skill_dict.get("name")),
        "category_label": meta.get("category_label", CATEGORY_LABELS.get(cat, cat)),
        "workflow": meta.get("workflow", []),
    }


def get_platform_catalog() -> dict:
    return {
        "platform": {
            "name": "企业智能体工作台",
            "product_code": "AgentWorkbench",
            "version": "1.0.0",
            "description": "面向企业场景的 LLM 智能体编排平台，集成工具调用、技能编排、知识增强与多智能体协同能力。",
        },
        "execution_modes": list(EXECUTION_MODES.values()),
        "agent_profiles": list(AGENT_PROFILES.values()),
        "category_labels": CATEGORY_LABELS,
        "tool_labels": {
            name: meta.get("display_name", name)
            for name, meta in TOOL_CATALOG.items()
        },
        "skill_labels": {
            name: meta.get("display_name", name)
            for name, meta in SKILL_CATALOG.items()
        },
        "provider_labels": {
            "deepseek": "DeepSeek",
            "openai": "OpenAI",
            "anthropic": "Claude",
            "custom": "本地模型",
        },
    }

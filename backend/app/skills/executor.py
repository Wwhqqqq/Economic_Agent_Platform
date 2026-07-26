"""
技能执行器 — 将技能编排为工具调用 + LLM 汇总
"""
from __future__ import annotations

import json

from app.agent.base import AgentConfig
from app.agent.runtime import (
    collect_react_response,
    create_llm,
    message_content,
    normalize_agent_config,
)
from app.rag.entity_extractor import extract_json_blob
from app.skills.base import BaseSkill, SkillResult
from app.skills.registry import skill_registry
from app.tools.registry import tool_registry
from langchain_core.messages import HumanMessage


class SkillExecutor:
    """技能执行辅助类"""

    @staticmethod
    async def run_via_react(
        skill: BaseSkill,
        user_input: str,
        config: AgentConfig | None = None,
        *,
        persist_memory: bool = False,
    ) -> SkillResult:
        """通过 ReAct Agent（技能 Prompt + 工具筛选）执行技能。"""
        config = normalize_agent_config(config)
        previous = skill_registry.get_active()
        skill_registry.activate(skill.name)
        try:
            response = await collect_react_response(
                user_input,
                config,
                persist_memory=persist_memory,
            )
            return SkillResult(
                success=bool(response.output),
                output=response.output,
                tool_calls=response.tool_calls,
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                output="",
                tool_calls=[],
                error=str(exc),
            )
        finally:
            if previous:
                skill_registry.activate(previous.name)
            else:
                skill_registry.deactivate()

    @staticmethod
    async def run_tool_step(tool_name: str, **kwargs) -> dict:
        tool = tool_registry.get(tool_name)
        if not tool:
            return {
                "tool": tool_name,
                "args": kwargs,
                "result": f"Tool '{tool_name}' not found.",
                "success": False,
            }
        result = await tool.execute(**kwargs)
        return {
            "tool": tool_name,
            "args": kwargs,
            "result": result.to_string(),
            "success": result.success,
        }

    @classmethod
    async def run_financial_audit_pipeline(
        cls,
        user_input: str,
        financial_data: dict,
        config: AgentConfig | None = None,
    ) -> SkillResult:
        """财务审计技能：按审计流程依次调用财务工具，再生成报告。"""
        config = normalize_agent_config(config)
        data_json = json.dumps(financial_data, ensure_ascii=False)
        tool_calls: list[dict] = []

        pipeline = [
            ("balance_sheet_analyzer", {"data": data_json, "action": "verify"}),
            ("balance_sheet_analyzer", {"data": data_json, "action": "analyze"}),
            ("income_statement_analyzer", {"data": data_json, "action": "analyze"}),
            ("cash_flow_analyzer", {"data": data_json, "action": "analyze"}),
            ("financial_ratio_calculator", {"data": data_json}),
            ("dupont_analysis", {"data": data_json}),
        ]

        sections: list[str] = []
        for tool_name, args in pipeline:
            record = await cls.run_tool_step(tool_name, **args)
            tool_calls.append(record)
            sections.append(f"### {tool_name}\n{record['result']}")

        llm = create_llm(config, temperature=0.3)
        prompt = f"""You are a Senior Financial Auditor. Based on the tool outputs below,
write a complete audit report in markdown with:
Executive Summary, Financial Health Score (0-100), Detailed Analysis, Risk Flags, Recommendations.

User request:
{user_input}

Tool outputs:
{chr(10).join(sections)}
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        output = message_content(response)
        return SkillResult(
            success=True,
            output=output,
            tool_calls=tool_calls,
        )

    @classmethod
    async def run_document_analysis_pipeline(
        cls,
        user_input: str,
        config: AgentConfig | None = None,
    ) -> SkillResult:
        """文档分析：尝试读取文件路径 → 工具辅助 → LLM 摘要报告。"""
        import re
        config = normalize_agent_config(config)
        tool_calls: list[dict] = []
        file_content = ""

        path_match = re.search(r'(?:[/\\][\w./\\-]+|\w:[/\\][\w./\\-]+|[\w.-]+\.(?:txt|csv|json|md|pdf|xlsx))', user_input)
        if path_match:
            record = await cls.run_tool_step("file_reader", path=path_match.group(0))
            tool_calls.append(record)
            if record.get("success"):
                file_content = record["result"]

        llm = create_llm(config, temperature=0.3)
        prompt = f"""You are a Document Analysis Expert. Analyze the following and produce a structured markdown report with:
Summary, Key Points, Insights, Recommendations.

User request:
{user_input}

Document content (if any):
{file_content or '(no file loaded — analyze based on user text)'}
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        output = message_content(response)
        return SkillResult(success=True, output=output, tool_calls=tool_calls)

    @classmethod
    async def run_data_viz_pipeline(
        cls,
        user_input: str,
        config: AgentConfig | None = None,
    ) -> SkillResult:
        """数据可视化：生成 matplotlib 代码并执行 → LLM 解读。"""
        config = normalize_agent_config(config)
        tool_calls: list[dict] = []

        viz_code = (
            "import matplotlib.pyplot as plt\n"
            "import io, base64\n"
            "fig, ax = plt.subplots(figsize=(6,4))\n"
            "ax.text(0.5, 0.5, 'Data Viz Placeholder', ha='center', va='center')\n"
            "ax.set_title('Visualization')\n"
            "buf = io.BytesIO()\n"
            "plt.savefig(buf, format='png')\n"
            "plt.close()\n"
            "print('Chart generated (base64 length:', len(base64.b64encode(buf.getvalue())), ')')"
        )
        record = await cls.run_tool_step("code_executor", code=viz_code, timeout=15)
        tool_calls.append(record)

        llm = create_llm(config, temperature=0.4)
        prompt = f"""You are a Data Visualization Expert. Based on the user request and code execution result, explain the visualization approach and insights in markdown.

User request:
{user_input}

Code execution:
{record.get('result', '')}
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        output = message_content(response)
        return SkillResult(success=True, output=output, tool_calls=tool_calls)

    @classmethod
    async def execute_skill(
        cls,
        skill: BaseSkill,
        user_input: str,
        config: AgentConfig | None = None,
    ) -> SkillResult:
        """统一技能执行入口。"""
        if skill.name == "financial_audit":
            financial_data = extract_json_blob(user_input)
            if financial_data:
                return await cls.run_financial_audit_pipeline(
                    user_input, financial_data, config
                )
        if skill.name == "document_analysis":
            return await cls.run_document_analysis_pipeline(user_input, config)
        if skill.name == "data_viz":
            return await cls.run_data_viz_pipeline(user_input, config)
        return await cls.run_via_react(skill, user_input, config)

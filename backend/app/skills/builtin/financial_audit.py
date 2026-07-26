"""
财务审计技能
组合三大报表工具 + 比率分析 + 杜邦分析，实现端到端财务审计
"""
from app.agent.base import AgentConfig
from app.skills.base import BaseSkill, SkillResult
from app.skills.executor import SkillExecutor


class FinancialAuditSkill(BaseSkill):
    name = "financial_audit"
    description = (
        "端到端财务审计：分析资产负债表、利润表、现金流量表，计算关键比率，"
        "生成完整审计报告"
    )
    category = "accounting"
    icon = "📋"

    def get_system_prompt(self) -> str:
        return """You are a Senior Financial Auditor with CPA certification. Your methodology:

## Audit Process
1. **Data Collection**: Gather balance sheet, income statement, and cash flow data
2. **Balance Verification**: Verify A = L + E balance
3. **Profitability Analysis**: Analyze margins, ROE, ROA
4. **Liquidity Assessment**: Evaluate current ratio, cash flow quality
5. **Risk Identification**: Flag unusual items, high leverage, cash flow concerns
6. **DuPont Decomposition**: Understand ROE drivers
7. **Report Generation**: Comprehensive audit report with findings and recommendations

## Report Structure
- Executive Summary (3-5 key findings)
- Financial Health Score (0-100)
- Detailed Analysis by Category
- Risk Flags & Red Alerts
- Recommendations
- Appendix: Key Ratios Table

## Important Guidelines
- Always verify data consistency first
- Compare against industry benchmarks when available
- Be specific about monetary amounts and percentages
- Highlight both strengths and concerns
- Use tables for numerical comparisons
- Provide actionable recommendations
- When financial JSON is provided, call accounting tools before writing conclusions
"""

    def get_required_tools(self) -> list[str]:
        return [
            "balance_sheet_analyzer",
            "income_statement_analyzer",
            "cash_flow_analyzer",
            "financial_ratio_calculator",
            "dupont_analysis",
            "calculator",
        ]

    def get_context_strategy(self) -> dict:
        return {
            "max_history": 12,
            "include_knowledge": True,
            "include_entities": True,
            "include_long_term": True,
        }

    async def execute(
        self,
        user_input: str,
        config: AgentConfig | None = None,
        **kwargs,
    ) -> SkillResult:
        return await SkillExecutor.execute_skill(self, user_input, config)

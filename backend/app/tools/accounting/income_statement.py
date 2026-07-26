"""
利润表分析工具
支持利润表数据的结构化分析、盈利能力评估
"""
import json
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class IncomeStatementInput(BaseModel):
    data: str = Field(description="利润表JSON数据，包含收入、成本、费用、利润各项")
    action: str = Field(
        default="analyze",
        description="操作: analyze(利润结构分析), margin(利润率计算), trend(同比分析)"
    )


class IncomeStatementTool(BaseTool):
    name = "income_statement_analyzer"
    description = (
        "分析利润表数据并评估盈利能力。"
        "操作：analyze（利润结构分析）、margin（毛利率/净利率/营业利润率）、trend（同比分析，需提供上期数据）。"
        "输入：利润表 JSON 数据及操作类型。"
    )
    category = "accounting"

    async def _execute(self, data: str, action: str = "analyze") -> ToolResult:
        try:
            pl = json.loads(data)
        except json.JSONDecodeError:
            return ToolResult(
                success=False, data=None,
                error="Invalid JSON format.",
            )

        if action == "analyze":
            return self._analyze_profit(pl)
        elif action == "margin":
            return self._compute_margins(pl)
        elif action == "trend":
            return self._trend_analysis(pl)
        else:
            return ToolResult(success=False, data=None, error=f"Unknown action: {action}")

    def _analyze_profit(self, pl: dict) -> ToolResult:
        revenue = pl.get("revenue", 0)
        cogs = pl.get("cost_of_goods_sold", 0)
        gross_profit = pl.get("gross_profit", revenue - cogs)
        operating_expenses = pl.get("operating_expenses", 0)
        operating_profit = pl.get("operating_profit", gross_profit - operating_expenses)
        net_profit = pl.get("net_profit", 0)

        lines = [
            "📊 Income Statement Analysis",
            "=" * 50,
            f"Revenue:              ¥{revenue:>15,.2f}",
            f"  Cost of Goods Sold: ¥{cogs:>15,.2f}",
            f"  Gross Profit:       ¥{gross_profit:>15,.2f}  "
            f"({gross_profit/revenue*100:.1f}% margin)" if revenue else "",
            f"",
            f"Operating Expenses:   ¥{operating_expenses:>15,.2f}",
            f"Operating Profit:     ¥{operating_profit:>15,.2f}  "
            f"({operating_profit/revenue*100:.1f}% margin)" if revenue else "",
            f"",
            f"Net Profit:           ¥{net_profit:>15,.2f}  "
            f"({net_profit/revenue*100:.1f}% margin)" if revenue else "",
        ]
        return ToolResult(success=True, data="\n".join(lines))

    def _compute_margins(self, pl: dict) -> ToolResult:
        revenue = pl.get("revenue", 1)
        gross_profit = pl.get("gross_profit", 0)
        operating_profit = pl.get("operating_profit", 0)
        net_profit = pl.get("net_profit", 0)
        ebitda = pl.get("ebitda", operating_profit)

        gross_margin = gross_profit / revenue * 100
        operating_margin = operating_profit / revenue * 100
        net_margin = net_profit / revenue * 100
        ebitda_margin = ebitda / revenue * 100

        def health(val, threshold):
            if val >= threshold * 1.2:
                return "✅ Excellent"
            elif val >= threshold:
                return "✅ Good"
            elif val >= threshold * 0.5:
                return "⚠️  Watch"
            else:
                return "🔴 Concern"

        return ToolResult(
            success=True,
            data=(
                f"📊 Profitability Margins\n"
                f"{'='*50}\n"
                f"Gross Margin:      {gross_margin:.1f}%  {health(gross_margin, 30)}\n"
                f"Operating Margin:  {operating_margin:.1f}%  {health(operating_margin, 15)}\n"
                f"Net Margin:        {net_margin:.1f}%  {health(net_margin, 10)}\n"
                f"EBITDA Margin:     {ebitda_margin:.1f}%\n"
            ),
        )

    def _trend_analysis(self, pl: dict) -> ToolResult:
        prev = pl.get("previous_period", {})
        if not prev:
            return ToolResult(
                success=False, data=None,
                error="No previous period data. Include 'previous_period' in JSON.",
            )

        items = ["revenue", "gross_profit", "operating_profit", "net_profit"]
        lines = ["📊 Year-over-Year Trend Analysis", "=" * 50]

        for item in items:
            curr_val = pl.get(item, 0)
            prev_val = prev.get(item, 0)
            if prev_val:
                change = (curr_val - prev_val) / abs(prev_val) * 100
                arrow = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                lines.append(
                    f"{arrow} {item:20s}: {change:+.1f}%  "
                    f"(¥{prev_val:,.0f} → ¥{curr_val:,.0f})"
                )

        return ToolResult(success=True, data="\n".join(lines))

    def get_input_schema(self):
        return IncomeStatementInput

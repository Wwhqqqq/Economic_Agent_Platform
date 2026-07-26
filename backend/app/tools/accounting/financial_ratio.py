"""
财务比率综合计算工具
支持四大类财务比率计算：盈利能力、偿债能力、营运能力、成长能力
"""
import json
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class FinancialRatioInput(BaseModel):
    data: str = Field(description="包含三大报表关键数据的JSON")
    categories: str = Field(
        default="all",
        description="比率类别: all, profitability(盈利), solvency(偿债), "
                    "efficiency(营运), growth(成长)"
    )


class FinancialRatioTool(BaseTool):
    name = "financial_ratio_calculator"
    description = (
        "基于财务报表数据计算综合财务比率。"
        "类别：profitability（盈利能力：ROE、ROA 等）、solvency（偿债能力：负债率等）、efficiency（营运能力：周转率）、growth（成长能力：同比增长）。"
        "输入：包含财务数据的 JSON 及类别选择。"
    )
    category = "accounting"

    async def _execute(self, data: str, categories: str = "all") -> ToolResult:
        try:
            fin = json.loads(data)
        except json.JSONDecodeError:
            return ToolResult(success=False, data=None, error="Invalid JSON format.")

        results = []

        if categories in ("all", "profitability"):
            results.append(self._profitability_ratios(fin))
        if categories in ("all", "solvency"):
            results.append(self._solvency_ratios(fin))
        if categories in ("all", "efficiency"):
            results.append(self._efficiency_ratios(fin))
        if categories in ("all", "growth"):
            results.append(self._growth_ratios(fin))

        return ToolResult(success=True, data="\n\n".join(results))

    def _profitability_ratios(self, fin: dict) -> str:
        net_profit = fin.get("net_profit", 0)
        revenue = fin.get("revenue", 1)
        total_assets = fin.get("total_assets", 1)
        total_equity = fin.get("total_equity", 1)
        gross_profit = fin.get("gross_profit", 0)

        roe = net_profit / total_equity * 100 if total_equity else 0
        roa = net_profit / total_assets * 100 if total_assets else 0
        npm = net_profit / revenue * 100 if revenue else 0
        gpm = gross_profit / revenue * 100 if revenue else 0

        def grade(val, benchmarks):
            for threshold, label in benchmarks:
                if val >= threshold:
                    return label
            return benchmarks[-1][1]

        roe_grade = grade(roe, [(20, "🏆"), (15, "✅"), (10, "⚠️"), (0, "🔴")])
        roa_grade = grade(roa, [(10, "🏆"), (5, "✅"), (2, "⚠️"), (0, "🔴")])

        return (
            f"📊 Profitability Ratios\n"
            f"{'='*50}\n"
            f"ROE  (Return on Equity):      {roe:6.1f}%  {roe_grade}\n"
            f"ROA  (Return on Assets):      {roa:6.1f}%  {roa_grade}\n"
            f"NPM  (Net Profit Margin):     {npm:6.1f}%\n"
            f"GPM  (Gross Profit Margin):   {gpm:6.1f}%"
        )

    def _solvency_ratios(self, fin: dict) -> str:
        total_assets = fin.get("total_assets", 1)
        total_liabilities = fin.get("total_liabilities", 0)
        total_equity = fin.get("total_equity", 1)
        current_assets = fin.get("current_assets", total_assets)
        current_liabilities = fin.get("current_liabilities", 1)

        debt_ratio = total_liabilities / total_assets * 100
        dte = total_liabilities / total_equity
        current_ratio = current_assets / current_liabilities

        return (
            f"📊 Solvency Ratios\n"
            f"{'='*50}\n"
            f"Debt Ratio:           {debt_ratio:6.1f}%  "
            f"{'✅' if debt_ratio < 50 else '⚠️'}\n"
            f"Debt-to-Equity:       {dte:6.2f}     "
            f"{'✅' if dte < 1 else '⚠️'}\n"
            f"Current Ratio:        {current_ratio:6.2f}     "
            f"{'✅' if current_ratio > 2 else '⚠️'}"
        )

    def _efficiency_ratios(self, fin: dict) -> str:
        revenue = fin.get("revenue", 1)
        total_assets = fin.get("total_assets", 1)
        inventory = fin.get("inventory", 1)
        receivables = fin.get("accounts_receivable", 1)

        asset_turnover = revenue / total_assets if total_assets else 0
        inventory_turnover = fin.get("cogs", revenue * 0.6) / inventory if inventory else 0
        receivable_turnover = revenue / receivables if receivables else 0

        return (
            f"📊 Efficiency Ratios\n"
            f"{'='*50}\n"
            f"Asset Turnover:       {asset_turnover:6.2f}x\n"
            f"Inventory Turnover:   {inventory_turnover:6.2f}x\n"
            f"Receivable Turnover:  {receivable_turnover:6.2f}x"
        )

    def _growth_ratios(self, fin: dict) -> str:
        prev = fin.get("previous_period", {})
        if not prev:
            return "📊 Growth Ratios\n" + "=" * 50 + "\n⚠️  No previous period data available."

        items = {
            "Revenue Growth": ("revenue", "revenue"),
            "Profit Growth": ("net_profit", "net_profit"),
            "Asset Growth": ("total_assets", "total_assets"),
        }

        lines = ["📊 Growth Ratios (YoY)", "=" * 50]
        for label, (curr_key, prev_key) in items.items():
            curr = fin.get(curr_key, 0)
            prev_val = prev.get(prev_key, 0)
            if prev_val:
                growth = (curr - prev_val) / abs(prev_val) * 100
                lines.append(f"{label:25s}: {growth:+6.1f}%")

        return "\n".join(lines)

    def get_input_schema(self):
        return FinancialRatioInput

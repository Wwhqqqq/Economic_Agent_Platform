"""
杜邦分析工具
将 ROE 分解为净利率 × 资产周转率 × 权益乘数
"""
import json
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class DupontInput(BaseModel):
    data: str = Field(description="包含净利率、资产周转率、权益乘数相关数据的JSON")


class DupontAnalysisTool(BaseTool):
    name = "dupont_analysis"
    description = (
        "执行杜邦分析，将 ROE 分解为净利率、资产周转率和权益乘数。"
        "公式：ROE = 净利率 × 资产周转率 × 权益乘数。"
        "帮助识别盈利能力的驱动因素。"
        "输入：包含财务数据的 JSON（net_profit、revenue、total_assets、total_equity）。"
    )
    category = "accounting"

    async def _execute(self, data: str) -> ToolResult:
        try:
            fin = json.loads(data)
        except json.JSONDecodeError:
            return ToolResult(success=False, data=None, error="Invalid JSON format.")

        net_profit = fin.get("net_profit", 0)
        revenue = fin.get("revenue", 1)
        total_assets = fin.get("total_assets", 1)
        total_equity = fin.get("total_equity", 1)

        npm = net_profit / revenue if revenue else 0
        at = revenue / total_assets if total_assets else 0
        em = total_assets / total_equity if total_equity else 0

        roe = npm * at * em
        roe_direct = net_profit / total_equity * 100 if total_equity else 0

        def driver_analysis(npm, at, em):
            """判断 ROE 的主要驱动因素"""
            normalized = [
                ("Net Profit Margin", npm),
                ("Asset Turnover", at),
                ("Equity Multiplier (Leverage)", em - 1),  # 减1看超额杠杆
            ]
            normalized.sort(key=lambda x: abs(x[1]), reverse=True)
            driver = normalized[0][0]
            return f"Primary driver: **{driver}**"

        # 三因子贡献度可视化
        bar = lambda val, total: "█" * int(val * 20 / total) if total else ""

        max_val = max(npm, at, em - 1, 0.01)

        return ToolResult(
            success=True,
            data=(
                f"📊 DuPont Analysis\n"
                f"{'='*60}\n\n"
                f"ROE = NPM × Asset Turnover × Equity Multiplier\n"
                f"       {npm:.4f}  ×     {at:.4f}      ×      {em:.4f}\n"
                f"       = {npm * at * em:.4f} = {npm * at * em * 100:.1f}%\n\n"
                f"Direct ROE check: {roe_direct:.1f}%  "
                f"{'✅ Matches' if abs(roe - npm * at * em) < 0.001 else '⚠️  Check data'}\n\n"
                f"{'='*60}\n"
                f"Component Breakdown:\n\n"
                f"1. Net Profit Margin:     {npm*100:6.2f}%  {bar(npm, max_val)}\n"
                f"   (Net Profit / Revenue)\n"
                f"   → ¥{net_profit:,.0f} / ¥{revenue:,.0f}\n\n"
                f"2. Asset Turnover:        {at:6.4f}   {bar(at, max_val)}\n"
                f"   (Revenue / Total Assets)\n"
                f"   → ¥{revenue:,.0f} / ¥{total_assets:,.0f}\n\n"
                f"3. Equity Multiplier:     {em:6.4f}   {bar(em - 1, max_val)}\n"
                f"   (Total Assets / Equity)\n"
                f"   → ¥{total_assets:,.0f} / ¥{total_equity:,.0f}\n\n"
                f"{'='*60}\n"
                f"💡 {driver_analysis(npm, at, em)}\n"
            ),
        )

    def get_input_schema(self):
        return DupontInput

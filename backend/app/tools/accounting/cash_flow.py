"""
现金流量表分析工具
支持现金流结构分析、自由现金流计算
"""
import json
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class CashFlowInput(BaseModel):
    data: str = Field(description="现金流量表JSON数据，包含经营/投资/筹资现金流")
    action: str = Field(
        default="analyze",
        description="操作: analyze(现金流结构分析), fcf(自由现金流), quality(盈利质量分析)"
    )


class CashFlowTool(BaseTool):
    name = "cash_flow_analyzer"
    description = (
        "分析现金流量表数据并评估现金生成能力。"
        "操作：analyze（现金流结构分析）、fcf（自由现金流计算）、quality（盈利质量分析，对比净利润与经营现金流）。"
        "输入：现金流量表 JSON 数据及操作类型。"
    )
    category = "accounting"

    async def _execute(self, data: str, action: str = "analyze") -> ToolResult:
        try:
            cf = json.loads(data)
        except json.JSONDecodeError:
            return ToolResult(
                success=False, data=None, error="Invalid JSON format.",
            )

        if action == "analyze":
            return self._analyze_flows(cf)
        elif action == "fcf":
            return self._compute_fcf(cf)
        elif action == "quality":
            return self._quality_check(cf)
        else:
            return ToolResult(success=False, data=None, error=f"Unknown action: {action}")

    def _analyze_flows(self, cf: dict) -> ToolResult:
        operating = cf.get("operating_cash_flow", 0)
        investing = cf.get("investing_cash_flow", 0)
        financing = cf.get("financing_cash_flow", 0)
        net_change = operating + investing + financing

        def sign_label(val):
            if val > 0:
                return "Inflow (+)"
            elif val < 0:
                return "Outflow (-)"
            return "Zero"

        return ToolResult(
            success=True,
            data=(
                f"📊 Cash Flow Statement Analysis\n"
                f"{'='*50}\n"
                f"Operating Activities:   ¥{operating:>12,.2f}  {sign_label(operating)}\n"
                f"Investing Activities:   ¥{investing:>12,.2f}  {sign_label(investing)}\n"
                f"Financing Activities:   ¥{financing:>12,.2f}  {sign_label(financing)}\n"
                f"{'-'*50}\n"
                f"Net Cash Change:        ¥{net_change:>12,.2f}\n"
                f"\n💡 Pattern Analysis: {self._pattern_analysis(operating, investing, financing)}"
            ),
        )

    def _pattern_analysis(self, op: float, inv: float, fin: float) -> str:
        """现金流模式分析"""
        if op > 0 and inv < 0 and fin < 0:
            return "🏆 Healthy Mature Company: Strong operations, actively investing, paying down debt"
        elif op > 0 and inv < 0 and fin > 0:
            return "📈 Growth Company: Strong operations, expanding aggressively, raising capital"
        elif op > 0 and inv > 0 and fin < 0:
            return "🔄 Restructuring: Selling assets, paying down debt"
        elif op < 0 and inv < 0 and fin > 0:
            return "🚀 Early Stage / Turnaround: Funding operations and investment externally"
        elif op < 0 and inv > 0 and fin > 0:
            return "⚠️  Distress Warning: Selling assets AND raising capital to cover losses"
        else:
            return "Mixed pattern - requires detailed investigation"

    def _compute_fcf(self, cf: dict) -> ToolResult:
        operating = cf.get("operating_cash_flow", 0)
        capex = cf.get("capital_expenditure", 0)
        fcf = operating + capex  # capex is usually negative

        return ToolResult(
            success=True,
            data=(
                f"📊 Free Cash Flow Analysis\n"
                f"{'='*40}\n"
                f"Operating Cash Flow:  ¥{operating:>12,.2f}\n"
                f"Capital Expenditure:  ¥{capex:>12,.2f}\n"
                f"{'-'*40}\n"
                f"Free Cash Flow:       ¥{fcf:>12,.2f}\n"
                f"\n"
                f"{'✅ FCF Positive - Good cash generation' if fcf > 0 else '⚠️  FCF Negative - Watch liquidity'}"
            ),
        )

    def _quality_check(self, cf: dict) -> ToolResult:
        operating_cf = cf.get("operating_cash_flow", 0)
        net_profit = cf.get("net_profit", 1)
        quality_ratio = operating_cf / net_profit if net_profit else 0

        if quality_ratio >= 0.8:
            assessment = "✅ High Quality: Operating CF covers {:.0%} of net profit".format(quality_ratio)
        elif quality_ratio >= 0.5:
            assessment = "⚠️  Moderate Quality: Operating CF covers {:.0%} of net profit".format(quality_ratio)
        else:
            assessment = "🔴 Low Quality: Operating CF covers only {:.0%} of net profit".format(quality_ratio)

        return ToolResult(
            success=True,
            data=(
                f"📊 Earnings Quality Assessment\n"
                f"{'='*50}\n"
                f"Net Profit:             ¥{net_profit:>12,.2f}\n"
                f"Operating Cash Flow:    ¥{operating_cf:>12,.2f}\n"
                f"Quality Ratio (OCF/NP): {quality_ratio:.2f}\n"
                f"\n{assessment}\n"
                f"\n💡 A ratio close to 1.0 indicates high earnings quality."
            ),
        )

    def get_input_schema(self):
        return CashFlowInput

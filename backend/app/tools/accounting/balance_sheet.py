"""
资产负债表分析工具
支持资产负债表数据的结构化分析与解读
"""
import json
from typing import Optional
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class BalanceSheetInput(BaseModel):
    data: str = Field(description="资产负债表JSON数据，包含资产、负债、所有者权益各项")
    action: str = Field(
        default="analyze",
        description="操作: analyze(结构分析), ratio(关键比率), verify(平衡验证)"
    )


class BalanceSheetTool(BaseTool):
    name = "balance_sheet_analyzer"
    description = (
        "分析资产负债表数据并计算关键财务指标。"
        "操作：analyze（结构分析）、ratio（流动比率、负债率等关键比率）、verify（验证 A = L + E 平衡）。"
        "输入：资产负债表 JSON 数据及操作类型。"
    )
    category = "accounting"

    async def _execute(self, data: str, action: str = "analyze") -> ToolResult:
        try:
            bs = json.loads(data)
        except json.JSONDecodeError:
            return ToolResult(
                success=False, data=None,
                error="Invalid JSON format. Please provide valid balance sheet data.",
            )

        if action == "verify":
            return self._verify_balance(bs)
        elif action == "ratio":
            return self._compute_ratios(bs)
        elif action == "analyze":
            return self._analyze_structure(bs)
        else:
            return ToolResult(
                success=False, data=None,
                error=f"Unknown action: {action}",
            )

    def _verify_balance(self, bs: dict) -> ToolResult:
        total_assets = bs.get("total_assets", 0)
        total_liabilities = bs.get("total_liabilities", 0)
        total_equity = bs.get("total_equity", 0)
        calculated = total_liabilities + total_equity

        balanced = abs(total_assets - calculated) < 0.01
        return ToolResult(
            success=True,
            data=(
                f"📊 Balance Sheet Verification\n"
                f"{'='*40}\n"
                f"Total Assets:      ¥{total_assets:,.2f}\n"
                f"Total Liabilities: ¥{total_liabilities:,.2f}\n"
                f"Total Equity:      ¥{total_equity:,.2f}\n"
                f"{'-'*40}\n"
                f"L + E:             ¥{calculated:,.2f}\n"
                f"{'='*40}\n"
                f"✅ Balanced: A = L + E"
                if balanced else
                f"⚠️  NOT Balanced! Difference: ¥{abs(total_assets - calculated):,.2f}"
            ),
        )

    def _compute_ratios(self, bs: dict) -> ToolResult:
        current_assets = bs.get("current_assets", bs.get("total_assets", 0))
        current_liabilities = bs.get("current_liabilities", bs.get("total_liabilities", 1))
        total_assets = bs.get("total_assets", 1)
        total_liabilities = bs.get("total_liabilities", 0)
        total_equity = bs.get("total_equity", 1)

        current_ratio = current_assets / current_liabilities if current_liabilities else 0
        debt_ratio = total_liabilities / total_assets if total_assets else 0
        equity_ratio = total_equity / total_assets if total_assets else 0
        debt_to_equity = total_liabilities / total_equity if total_equity else 0

        return ToolResult(
            success=True,
            data=(
                f"📊 Balance Sheet Key Ratios\n"
                f"{'='*40}\n"
                f"Current Ratio:        {current_ratio:.2f}  "
                f"{'✅ Healthy (>2.0)' if current_ratio > 2 else '⚠️  Watch (<2.0)'}\n"
                f"Debt Ratio:           {debt_ratio:.2%}   "
                f"{'✅ Safe (<50%)' if debt_ratio < 0.5 else '⚠️  High (>50%)'}\n"
                f"Equity Ratio:         {equity_ratio:.2%}\n"
                f"Debt-to-Equity:       {debt_to_equity:.2f}  "
                f"{'✅ Safe (<1.0)' if debt_to_equity < 1 else '⚠️  High (>1.0)'}\n"
            ),
        )

    def _analyze_structure(self, bs: dict) -> ToolResult:
        total_assets = bs.get("total_assets", 1)
        total_liabilities = bs.get("total_liabilities", 0)
        total_equity = bs.get("total_equity", 0)

        lines = [
            "📊 Balance Sheet Structural Analysis",
            "=" * 50,
            f"Total Assets:       ¥{total_assets:>15,.2f}  (100.0%)",
        ]

        for key in ["current_assets", "non_current_assets", "fixed_assets", "intangible_assets"]:
            val = bs.get(key)
            if val is not None:
                pct = val / total_assets * 100
                lines.append(f"  ├─ {key:25s} ¥{val:>12,.2f}  ({pct:.1f}%)")

        lines.append(f"\nTotal Liabilities:  ¥{total_liabilities:>15,.2f}  ({total_liabilities/total_assets*100:.1f}%)")
        for key in ["current_liabilities", "non_current_liabilities", "long_term_debt"]:
            val = bs.get(key)
            if val is not None:
                pct = val / total_assets * 100
                lines.append(f"  ├─ {key:25s} ¥{val:>12,.2f}  ({pct:.1f}%)")

        lines.append(f"\nTotal Equity:       ¥{total_equity:>15,.2f}  ({total_equity/total_assets*100:.1f}%)")
        for key in ["share_capital", "retained_earnings", "reserves"]:
            val = bs.get(key)
            if val is not None:
                pct = val / total_assets * 100
                lines.append(f"  ├─ {key:25s} ¥{val:>12,.2f}  ({pct:.1f}%)")

        return ToolResult(success=True, data="\n".join(lines))

    def get_input_schema(self):
        return BalanceSheetInput

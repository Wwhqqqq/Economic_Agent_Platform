"""
数学计算工具
支持复杂数学表达式的安全求值
"""
import math
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class CalculatorInput(BaseModel):
    expression: str = Field(description="要计算的数学表达式，如 '2 + 3 * 4' 或 'sqrt(144)'")


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "计算数学表达式。"
        "支持基本运算（+、-、*、/、**、%）、"
        "数学函数（sqrt、sin、cos、log、abs、pow）"
        "以及常数（pi、e）。"
        "输入：数学表达式字符串。"
    )
    category = "general"

    # 安全白名单：只允许这些内置函数
    _SAFE_FUNCTIONS = {
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "sum": sum,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log, "log10": math.log10,
        "log2": math.log2, "exp": math.exp,
        "floor": math.floor, "ceil": math.ceil,
        "pi": math.pi, "e": math.e,
        "radians": math.radians, "degrees": math.degrees,
    }

    async def _execute(self, expression: str) -> ToolResult:
        try:
            # 安全求值：只允许白名单中的函数
            result = eval(
                expression,
                {"__builtins__": {}},
                self._SAFE_FUNCTIONS,
            )
            return ToolResult(
                success=True,
                data=f"Expression: {expression}\nResult: {result}",
            )
        except SyntaxError as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid expression syntax: {e}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Calculation error: {e}",
            )

    def get_input_schema(self):
        return CalculatorInput

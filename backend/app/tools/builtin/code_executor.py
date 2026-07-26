"""
代码执行工具 — 带超时限制
"""
import asyncio
import io
import sys
import traceback
import concurrent.futures
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class CodeExecutorInput(BaseModel):
    code: str = Field(description="要执行的 Python 代码")
    timeout: int = Field(default=10, description="执行超时时间（秒）")


def _run_code(code: str) -> tuple[bool, str]:
    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()
    try:
        exec(code, {"__builtins__": __builtins__})
        output = captured.getvalue()
        return True, output if output else "(no output)"
    except Exception:
        return False, traceback.format_exc()
    finally:
        sys.stdout = old_stdout


class CodeExecutorTool(BaseTool):
    name = "code_executor"
    description = (
        "在受限环境中执行 Python 代码。"
        "可用于计算、数据处理或快速脚本编写。"
        "输入：Python 代码字符串。"
    )
    category = "general"

    async def _execute(self, code: str, timeout: int = 10) -> ToolResult:
        loop = asyncio.get_event_loop()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = loop.run_in_executor(pool, _run_code, code)
                success, output = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                data=None,
                error=f"Execution timed out after {timeout}s",
            )

        if success:
            return ToolResult(success=True, data=f"Execution result:\n{output}")
        return ToolResult(success=False, data=None, error=output)

    def get_input_schema(self):
        return CodeExecutorInput

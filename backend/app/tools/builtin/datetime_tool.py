"""
日期时间工具
获取当前时间、日期计算等
"""
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class DateTimeInput(BaseModel):
    action: str = Field(
        default="now",
        description="操作类型: now(当前时间), today(今天日期), weekday(星期几), "
                    "add_days(加N天, 需传入days参数), diff_days(日期差, 需传入date1和date2)"
    )
    days: int = Field(default=0, description="加减天数（用于 add_days 操作）")
    date1: str = Field(default="", description="第一个日期（YYYY-MM-DD格式）")
    date2: str = Field(default="", description="第二个日期（YYYY-MM-DD格式）")


class DateTimeTool(BaseTool):
    name = "datetime"
    description = (
        "获取当前日期时间或执行日期计算。"
        "操作：now（当前时间）、today（今天日期）、weekday（星期几）、add_days（日期加减）、diff_days（日期差）。"
        "输入：操作类型字符串和可选参数。"
    )
    category = "general"

    async def _execute(
        self,
        action: str = "now",
        days: int = 0,
        date1: str = "",
        date2: str = "",
    ) -> ToolResult:
        now = datetime.now()

        try:
            if action == "now":
                return ToolResult(
                    success=True,
                    data=f"Current datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}",
                )
            elif action == "today":
                return ToolResult(
                    success=True,
                    data=f"Today: {now.strftime('%Y-%m-%d')}",
                )
            elif action == "weekday":
                weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                return ToolResult(
                    success=True,
                    data=f"Today is {weekdays[now.weekday()]}",
                )
            elif action == "add_days":
                target = now + timedelta(days=days)
                return ToolResult(
                    success=True,
                    data=f"{days} days from now: {target.strftime('%Y-%m-%d')}",
                )
            elif action == "diff_days":
                d1 = datetime.strptime(date1, "%Y-%m-%d")
                d2 = datetime.strptime(date2, "%Y-%m-%d")
                diff = abs((d2 - d1).days)
                return ToolResult(
                    success=True,
                    data=f"Difference between {date1} and {date2}: {diff} days",
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Unknown action: {action}. Available: now, today, weekday, add_days, diff_days",
                )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def get_input_schema(self):
        return DateTimeInput

"""
工具基类 — 统一工具抽象层

每个工具都是可被 Agent 调用的独立功能单元。
继承 BaseTool 并实现 execute 方法即可创建新工具。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from pydantic import BaseModel
from langchain_core.tools import StructuredTool


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None

    def to_string(self) -> str:
        if self.success:
            return str(self.data)
        return f"Error: {self.error}"


class BaseTool(ABC):
    """
    工具抽象基类

    属性:
        name: 工具唯一标识
        description: 工具功能描述（用于 Agent 选择工具）
        category: 工具分类 (general / accounting / file / web)
        requires_confirmation: 执行前是否需要用户确认
    """

    name: str = ""
    description: str = ""
    category: str = "general"
    requires_confirmation: bool = False

    @abstractmethod
    async def _execute(self, **kwargs) -> ToolResult:
        """核心执行逻辑，子类必须实现"""
        ...

    def get_input_schema(self) -> type[BaseModel]:
        """返回工具的输入参数模型，子类可重写"""
        return BaseModel

    def to_langchain_tool(self) -> StructuredTool:
        """
        将自定义工具转换为 LangChain StructuredTool
        使用 Runnable 表达式风格的函数式转换
        """
        return StructuredTool.from_function(
            func=self._sync_execute_wrapper,
            name=self.name,
            description=self.description,
            args_schema=self.get_input_schema(),
        )

    def _sync_execute_wrapper(self, **kwargs) -> str:
        """同步包装器，用于 LangChain 工具接口"""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._execute(**kwargs))
                result = future.result()
        else:
            result = asyncio.run(self._execute(**kwargs))

        return result.to_string()

    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具（带前置检查和后置处理）
        这是外部调用的入口
        """
        # 前置处理：日志、权限检查等
        print(f"[Tool] Executing '{self.name}' with args: {kwargs}")

        try:
            result = await self._execute(**kwargs)
            print(f"[Tool] '{self.name}' completed: {result.success}")
            return result
        except Exception as e:
            print(f"[Tool] '{self.name}' failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def to_dict(self) -> dict:
        """序列化为前端展示用的字典"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "requires_confirmation": self.requires_confirmation,
        }

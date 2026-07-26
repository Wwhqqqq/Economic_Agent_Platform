"""
工具注册中心 — 动态工具管理

支持：
1. 代码级注册（内置工具）
2. 运行时注册/卸载（通过 API）
3. 按分类筛选工具
4. 批量转换为 LangChain 工具列表
"""
from typing import Optional
from langchain_core.tools import StructuredTool

from app.tools.base import BaseTool


class ToolRegistry:
    """工具注册中心（单例模式）"""

    _instance: Optional["ToolRegistry"] = None

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._tool_metadata: dict[str, dict] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """注册一个工具"""
        if tool.name in self._tools:
            print(f"[Registry] Tool '{tool.name}' already registered, overwriting.")
        self._tools[tool.name] = tool
        self._tool_metadata[tool.name] = tool.to_dict()
        print(f"[Registry] Registered tool: {tool.name} ({tool.category})")

    def unregister(self, name: str) -> bool:
        """卸载工具"""
        if name in self._tools:
            del self._tools[name]
            del self._tool_metadata[name]
            print(f"[Registry] Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """获取单个工具"""
        return self._tools.get(name)

    def get_by_category(self, category: str) -> list[BaseTool]:
        """按分类获取工具列表"""
        return [t for t in self._tools.values() if t.category == category]

    def list_all(self) -> list[dict]:
        """列出所有工具的元数据"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "requires_confirmation": t.requires_confirmation,
            }
            for t in self._tools.values()
        ]

    def list_categories(self) -> list[str]:
        """列出所有工具分类"""
        return list(set(t.category for t in self._tools.values()))

    def to_langchain_tools(
        self, categories: list[str] = None, names: list[str] = None
    ) -> list[StructuredTool]:
        """
        转换为 LangChain 工具列表，支持按分类或名称筛选

        Args:
            categories: 只包含指定分类的工具
            names: 只包含指定名称的工具

        这是连接自定义工具系统和 LangChain Agent 的关键方法
        """
        tools = []

        for tool in self._tools.values():
            if categories and tool.category not in categories:
                continue
            if names and tool.name not in names:
                continue
            tools.append(tool.to_langchain_tool())

        print(f"[Registry] Converted {len(tools)} tools to LangChain format")
        return tools

    def get_tool_count(self) -> int:
        return len(self._tools)


# 全局工具注册单例
tool_registry = ToolRegistry.get_instance()

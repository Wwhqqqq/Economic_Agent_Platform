"""
网络搜索工具
支持通过 DuckDuckGo 进行网页搜索
"""
import json
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class WebSearchInput(BaseModel):
    query: str = Field(description="搜索查询关键词")
    max_results: int = Field(default=5, description="最大返回结果数")


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "在互联网上搜索信息。"
        "用于查找最新动态、事实、文档或本地知识库中缺少的任何信息。"
        "输入：搜索关键词和可选的返回结果数。"
    )
    category = "web"

    async def _execute(self, query: str, max_results: int = 5) -> ToolResult:
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", ""),
                    })

            if not results:
                return ToolResult(
                    success=True,
                    data=f"No results found for '{query}'.",
                )

            formatted = "\n\n".join(
                f"[{i+1}] {r['title']}\n{r['snippet']}\n🔗 {r['url']}"
                for i, r in enumerate(results)
            )
            return ToolResult(success=True, data=formatted)

        except ImportError:
            return ToolResult(
                success=False,
                data=None,
                error="duckduckgo_search not installed. Run: pip install duckduckgo-search",
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def get_input_schema(self):
        return WebSearchInput

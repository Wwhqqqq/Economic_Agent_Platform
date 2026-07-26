"""工具管理 API"""
from fastapi import APIRouter

from app.tools.registry import tool_registry
from app.core.catalog import enrich_tool, CATEGORY_LABELS

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
async def list_tools(category: str = None):
    """获取所有工具或按分类筛选"""
    if category:
        tools = tool_registry.get_by_category(category)
        enriched = [enrich_tool(t.to_dict()) for t in tools]
        return {
            "tools": enriched,
            "category": category,
            "category_label": CATEGORY_LABELS.get(category, category),
        }
    raw = tool_registry.list_all()
    enriched = [enrich_tool(t) for t in raw]
    return {
        "tools": enriched,
        "categories": [
            {"key": c, "label": CATEGORY_LABELS.get(c, c)}
            for c in tool_registry.list_categories()
        ],
        "total": tool_registry.get_tool_count(),
    }


@router.get("/{tool_name}")
async def get_tool(tool_name: str):
    """获取工具详情"""
    tool = tool_registry.get(tool_name)
    if not tool:
        return {"error": f"Tool '{tool_name}' not found"}, 404
    return enrich_tool(tool.to_dict())

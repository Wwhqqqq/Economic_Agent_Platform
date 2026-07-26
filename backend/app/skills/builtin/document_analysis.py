"""
文档分析技能
组合文件读取 + 网络搜索 + 代码执行，实现端到端文档智能分析
"""
from app.agent.base import AgentConfig
from app.skills.base import BaseSkill, SkillResult
from app.skills.executor import SkillExecutor


class DocumentAnalysisSkill(BaseSkill):
    name = "document_analysis"
    description = "深度文档分析：读取、摘要、提取关键信息并对比多个文档"
    category = "document"
    icon = "📄"

    def get_system_prompt(self) -> str:
        return """You are a Document Analysis Expert. Your capabilities:

1. Read and parse documents (CSV, Excel, PDF, TXT, JSON)
2. Extract key information and summarize content
3. Identify patterns, anomalies, and insights
4. Compare multiple documents and highlight differences
5. Generate structured reports

When analyzing documents:
- Start by reading the file to understand its structure
- Identify the most important data points
- Look for trends, outliers, and notable patterns
- Present findings in a clear, structured format
- Use tables for numerical data when helpful
- Use file_reader when a path is mentioned; use web_search for external facts
"""

    def get_required_tools(self) -> list[str]:
        return ["file_reader", "calculator", "code_executor", "web_search"]

    def get_context_strategy(self) -> dict:
        return {
            "max_history": 16,
            "include_knowledge": True,
            "include_entities": True,
            "include_long_term": True,
        }

    async def execute(
        self,
        user_input: str,
        config: AgentConfig | None = None,
        **kwargs,
    ) -> SkillResult:
        return await SkillExecutor.execute_skill(self, user_input, config)

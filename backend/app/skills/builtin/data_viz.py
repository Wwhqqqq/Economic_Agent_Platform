"""
数据可视化技能
通过代码执行生成图表，辅助数据分析
"""
from app.agent.base import AgentConfig
from app.skills.base import BaseSkill, SkillResult
from app.skills.executor import SkillExecutor


class DataVisualizationSkill(BaseSkill):
    name = "data_visualization"
    description = "基于结构化数据生成数据可视化图表"
    category = "data"
    icon = "📊"

    def get_system_prompt(self) -> str:
        return """You are a Data Visualization Specialist. Your capabilities:

1. Parse structured data from files or user input
2. Choose appropriate chart types (bar, line, pie, scatter, etc.)
3. Generate charts using Python (matplotlib/seaborn)
4. Explain the insights revealed by each visualization
5. Suggest additional visualizations for better understanding

When creating visualizations:
- Use code_executor to generate matplotlib charts
- Print chart insights in plain language after running code
- Use file_reader when the user references a local data file
"""

    def get_required_tools(self) -> list[str]:
        return ["file_reader", "code_executor", "calculator"]

    def get_context_strategy(self) -> dict:
        return {
            "max_history": 10,
            "include_knowledge": True,
            "include_entities": False,
            "include_long_term": False,
        }

    async def execute(
        self,
        user_input: str,
        config: AgentConfig | None = None,
        **kwargs,
    ) -> SkillResult:
        return await SkillExecutor.execute_skill(self, user_input, config)

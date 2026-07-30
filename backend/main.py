"""
Agent Platform - FastAPI Main Entry

Start:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
import sys
import os

# Fix GBK encoding issue on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.tools import router as tools_router
from app.api.skills import router as skills_router
from app.api.agents import router as agents_router
from app.api.knowledge import router as knowledge_router
from app.api.settings import router as settings_router
from app.api.catalog import router as catalog_router
from app.api.auth import router as auth_router
from app.api.system import router as system_router
from app.api.audit import router as audit_router
from app.api.experts import router as experts_router


# ---- 自动注册所有内置工具 ----

def register_all_tools():
    """自动注册所有内置工具"""
    from app.tools.registry import tool_registry

    # 通用工具
    from app.tools.builtin.web_search import WebSearchTool
    from app.tools.builtin.calculator import CalculatorTool
    from app.tools.builtin.file_reader import FileReaderTool
    from app.tools.builtin.code_executor import CodeExecutorTool
    from app.tools.builtin.datetime_tool import DateTimeTool

    tool_registry.register(WebSearchTool())
    tool_registry.register(CalculatorTool())
    tool_registry.register(FileReaderTool())
    tool_registry.register(CodeExecutorTool())
    tool_registry.register(DateTimeTool())

    # 会计学工具
    from app.tools.accounting.balance_sheet import BalanceSheetTool
    from app.tools.accounting.income_statement import IncomeStatementTool
    from app.tools.accounting.cash_flow import CashFlowTool
    from app.tools.accounting.financial_ratio import FinancialRatioTool
    from app.tools.accounting.dupont_analysis import DupontAnalysisTool

    tool_registry.register(BalanceSheetTool())
    tool_registry.register(IncomeStatementTool())
    tool_registry.register(CashFlowTool())
    tool_registry.register(FinancialRatioTool())
    tool_registry.register(DupontAnalysisTool())

    print(f"[Startup] Registered {tool_registry.get_tool_count()} tools")


def register_all_skills():
    """自动注册所有内置技能"""
    from app.skills.registry import skill_registry

    from app.skills.builtin.document_analysis import DocumentAnalysisSkill
    from app.skills.builtin.data_viz import DataVisualizationSkill
    from app.skills.builtin.financial_audit import FinancialAuditSkill

    skill_registry.register(DocumentAnalysisSkill())
    skill_registry.register(DataVisualizationSkill())
    skill_registry.register(FinancialAuditSkill())

    print(f"[Startup] Registered {skill_registry.skill_count} skills")


# ---- 创建 FastAPI 应用 ----

app = FastAPI(
    title="企业智能体工作台",
    description="面向企业场景的 LLM 智能体编排平台：工具调用、技能编排、知识增强、多智能体协同",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)
app.include_router(tools_router)
app.include_router(skills_router)
app.include_router(agents_router)
app.include_router(knowledge_router)
app.include_router(settings_router)
app.include_router(catalog_router)
app.include_router(auth_router)
app.include_router(system_router)
app.include_router(audit_router)
app.include_router(experts_router)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    from app.core.settings_store import apply_persisted_settings
    from app.core.database import init_db
    from app.services.seed import seed_initial_data

    apply_persisted_settings()

    try:
        await init_db()
        await seed_initial_data()
        print("[Startup] MySQL schema ready")
    except Exception as exc:
        print(f"[Startup] MySQL init skipped: {exc}")

    try:
        from app.services.redis_init import init_redis_layout
        await init_redis_layout()
        print("[Startup] Redis layout ready")
    except Exception as exc:
        print(f"[Startup] Redis init skipped: {exc}")

    print("=" * 60)
    print(">>> 企业智能体工作台启动中...")
    print("=" * 60)

    # Register tools and skills
    register_all_tools()
    register_all_skills()

    # Available LLM Providers
    from app.llm.factory import LLMFactory
    providers = LLMFactory.list_providers()
    print("\n[LLM] Available Providers:")
    for p in providers:
        print(f"  - {p['name']}: {p['model']}")

    print(f"\n[DOCS] API Documentation: http://localhost:8000/api/docs")
    print(f"[WS]   WebSocket: ws://localhost:8000/ws/chat/{{session_id}}")
    print("=" * 60)


@app.get("/")
async def root():
    return {
        "name": "企业智能体工作台",
        "product_code": "AgentWorkbench",
        "version": "1.0.0",
        "docs": "/api/docs",
        "websocket": "/ws/chat/{session_id}",
    }


@app.get("/health/live")
async def health_live():
    """Liveness probe — process is up; used by Docker HEALTHCHECK."""
    return {"status": "alive"}


@app.get("/health")
async def health_check():
    from app.services.health import get_system_status
    status = await get_system_status()
    code = 200 if status["status"] in ("healthy", "degraded") else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(content=status, status_code=code)

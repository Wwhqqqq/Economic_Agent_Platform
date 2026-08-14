@echo off
chcp 65001 >nul
echo ============================================
echo   Agent Platform - 本地 Docker 基础设施
echo   MySQL + Redis + ChromaDB + Neo4j
echo ============================================
echo.

cd /d "%~dp0.."

if not exist ".env" (
  echo [信息] 复制 .env.example -> .env
  copy .env.example .env
)

echo [1/2] 启动 Docker 容器...
docker compose up -d
if errorlevel 1 (
  echo [错误] Docker 启动失败。请确认 Docker Desktop 已运行。
  exit /b 1
)

echo.
echo [2/2] 等待服务就绪...
timeout /t 15 /nobreak >nul
docker compose ps

echo.
echo ============================================
echo   基础设施已启动
echo   MySQL   : localhost:3306
echo   Redis   : localhost:6379
echo   Chroma  : localhost:8001
echo   Neo4j   : bolt://localhost:7688
echo.
echo   下一步:
echo     cd backend
echo     python -m scripts.seed_member_knowledge
echo     python -m uvicorn main:app --reload --port 8000
echo.
echo     cd frontend
echo     npm run dev
echo ============================================

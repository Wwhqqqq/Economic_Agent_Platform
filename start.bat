@echo off
chcp 65001 >nul
echo ============================================
echo   Agent Platform - 一键启动脚本 (Windows)
echo ============================================
echo.

REM 1. Check .env file
if not exist ".env" (
    echo [信息] 未找到 .env 文件，从 .env.example 创建...
    copy .env.example .env
    echo [信息] 请编辑 .env 文件填入你的 API Key
    echo.
)

REM 2. Start Docker services
echo [1/4] 启动 Docker 服务 (Neo4j + ChromaDB)...
docker-compose up -d
echo.

REM 3. Wait for services
echo [2/4] 等待数据库就绪...
timeout /t 5 /nobreak >nul
echo.

REM 4. Install Python dependencies
echo [3/4] 安装后端依赖...
cd backend
pip install -r requirements.txt -q
cd ..
echo.

REM 5. Start backend
echo [4/4] 启动后端服务...
echo    API 文档: http://localhost:8000/api/docs
echo    WebSocket: ws://localhost:8000/ws/chat/{session_id}
echo.
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd ..

echo.
echo ============================================
echo   启动完成！
echo   后端: http://localhost:8000
echo   API文档: http://localhost:8000/api/docs
echo ============================================
pause

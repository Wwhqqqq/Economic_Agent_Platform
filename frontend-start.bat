@echo off
chcp 65001 >nul
echo ============================================
echo   Agent Platform - 前端启动脚本
echo ============================================
echo.

cd frontend

REM Install dependencies if needed
if not exist "node_modules" (
    echo [1/2] 安装前端依赖...
    call npm install
    echo.
)

echo [2/2] 启动 Vite 开发服务器...
echo   前端地址: http://localhost:3000
echo.
call npm run dev

pause

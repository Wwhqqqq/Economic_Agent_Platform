#!/bin/bash
set -e

echo "============================================"
echo "  Agent Platform - 一键启动脚本 (Linux/Mac)"
echo "============================================"
echo ""

# 1. Check .env
if [ ! -f ".env" ]; then
    echo "[INFO] Creating .env from .env.example..."
    cp .env.example .env
    echo "[INFO] Please edit .env with your API keys"
    echo ""
fi

# 2. Start Docker services
echo "[1/4] Starting Docker services (Neo4j + ChromaDB)..."
docker-compose up -d
echo ""

# 3. Wait for services
echo "[2/4] Waiting for databases to be ready..."
sleep 5
echo ""

# 4. Install Python dependencies
echo "[3/4] Installing backend dependencies..."
cd backend
pip install -r requirements.txt -q
cd ..
echo ""

# 5. Start backend
echo "[4/4] Starting backend server..."
echo "  API Docs: http://localhost:8000/api/docs"
echo "  WebSocket: ws://localhost:8000/ws/chat/{session_id}"
echo ""
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

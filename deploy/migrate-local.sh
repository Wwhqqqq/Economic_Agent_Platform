#!/usr/bin/env bash
# 本地增量迁移（Batch 1–5：003 → 006）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/backend"

echo "== Alembic: 当前版本"
python -m alembic current || true

echo ""
echo "== Alembic: upgrade head (003_knowledge_chunks → 006_media_vlm)"
python -m alembic upgrade head

echo ""
echo "== Alembic: 迁移后版本"
python -m alembic current

echo ""
echo "完成。请重启后端: cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

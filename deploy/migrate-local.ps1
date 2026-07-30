# 本地增量迁移（Batch 1–5：003 → 006）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $Root "backend")

Write-Host "== Alembic: 当前版本"
python -m alembic current

Write-Host ""
Write-Host "== Alembic: upgrade head (003_knowledge_chunks -> 006_media_vlm)"
python -m alembic upgrade head

Write-Host ""
Write-Host "== Alembic: 迁移后版本"
python -m alembic current

Write-Host ""
Write-Host "完成。请重启后端:"
Write-Host "  cd backend"
Write-Host "  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

#!/usr/bin/env bash
# =============================================================================
# 部署后 RAG 灌库 + 验证（会员专享知识库）
#
# 在 one-click-deploy / incremental-update 完成后执行，或单独运行：
#   cd /opt/apps/agent-platform
#   bash deploy/post-deploy-rag.sh
#
# 环境变量:
#   FORCE_SEED=1   强制重建会员知识库索引
#   SKIP_SEED=1    跳过灌库（仅验证）
# =============================================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/apps/agent-platform}"
COMPOSE_BASE="deploy/docker-compose.prod.yml"
COMPOSE_MYSQL="deploy/docker-compose.prod.external-mysql.yml"
COMPOSE_FILE_ARGS=(-f "${COMPOSE_BASE}")
FORCE_FLAG=""
[[ "${FORCE_SEED:-0}" == "1" ]] && FORCE_FLAG="--force"

STEP=0
log()  { STEP=$((STEP + 1)); echo ""; echo "== [RAG ${STEP}] $*"; }
info() { echo "    $*"; }
die()  { echo "[ERROR] $*" >&2; exit 1; }

cd "${APP_DIR}" || die "目录不存在: ${APP_DIR}"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source <(grep -E '^(MYSQL_DOCKER_NETWORK|DEPLOY_PORT)=' .env | sed 's/^/export /') || true
fi

if [[ -n "${MYSQL_DOCKER_NETWORK:-}" ]] && [[ -f "${COMPOSE_MYSQL}" ]]; then
  COMPOSE_FILE_ARGS+=(-f "${COMPOSE_MYSQL}")
fi

compose() {
  docker compose "${COMPOSE_FILE_ARGS[@]}" --project-directory . "$@"
}

wait_container_healthy() {
  local name="$1" timeout="${2:-120}" elapsed=0
  info "等待容器健康: ${name}"
  while (( elapsed < timeout )); do
    local status
    status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$name" 2>/dev/null || echo "missing")
    if [[ "$status" == "healthy" || "$status" == "running" ]]; then
      info "${name} → ${status}"
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done
  die "容器未就绪: ${name} (timeout ${timeout}s)"
}

log "确保基础设施容器运行"
compose up -d redis chromadb neo4j
wait_container_healthy "agent-prod-redis" 60
wait_container_healthy "agent-prod-chromadb" 90 || info "Chroma 无 healthcheck，继续..."
wait_container_healthy "agent-prod-neo4j" 120

if [[ "${SKIP_SEED:-0}" != "1" ]]; then
  log "灌库会员专享知识库 (visibility=member)"
  if [[ -d "data/member_knowledge" ]]; then
    info "语料目录: data/member_knowledge ($(find data/member_knowledge -name '*.md' | wc -l) 篇 md)"
  else
    die "缺少 data/member_knowledge，请确认 git pull 完整"
  fi

  compose run --rm --no-deps backend python -m scripts.seed_member_knowledge ${FORCE_FLAG}
  info "灌库命令已完成"
else
  log "跳过灌库 (SKIP_SEED=1)"
fi

log "验证 RAG 与知识库"
compose run --rm --no-deps backend python - <<'PY'
import asyncio
import os
import sys

from sqlalchemy import create_engine, text, func, select

sys.path.insert(0, "/app/backend")
os.chdir("/app/backend")

from dotenv import load_dotenv
load_dotenv("/app/.env", override=True)

from app.db.chroma import get_chroma_client
from app.db.neo4j import get_neo4j_client
from app.rag.vector_store import KNOWLEDGE_COLLECTION

errors = []

# MySQL member docs
db_url = os.getenv("DATABASE_URL", "").replace("+aiomysql", "+pymysql")
if db_url:
    eng = create_engine(db_url)
    with eng.connect() as conn:
        row = conn.execute(
            text(
                "SELECT COUNT(*) AS c, COALESCE(SUM(chunk_count),0) AS chunks "
                "FROM knowledge_documents "
                "WHERE visibility='member' AND deleted_at IS NULL AND parse_status='ready'"
            )
        ).one()
        doc_count, chunk_total = int(row.c), int(row.chunks)
        print(f"[MySQL] member docs ready: {doc_count}, chunks sum: {chunk_total}")
        if doc_count < 15:
            errors.append(f"member docs too few: {doc_count} (expected >= 15)")
else:
    errors.append("DATABASE_URL missing")

# Chroma
try:
    chroma = get_chroma_client()
    mode = "remote" if chroma.is_remote else "local"
    count = chroma.count(KNOWLEDGE_COLLECTION)
    print(f"[Chroma] mode={mode}, collection={KNOWLEDGE_COLLECTION}, vectors~={count}")
    if count < 50:
        errors.append(f"chroma doc count low: {count} (expected >= 50 after seed)")
except Exception as e:
    errors.append(f"chroma: {e}")

# Neo4j
try:
    neo = get_neo4j_client()
    if neo.available:
        print(f"[Neo4j] documents={neo.count_documents()}, entities={neo.count_entities()}")
    else:
        errors.append("neo4j unavailable")
except Exception as e:
    errors.append(f"neo4j: {e}")

if errors:
    print("\n[VERIFY FAILED]")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print("\n[VERIFY OK] RAG member knowledge library ready")
PY

log "RAG  post-deploy 完成"

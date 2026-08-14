#!/usr/bin/env bash
# =============================================================================
# 全栈健康检查 — 所有 Docker 容器 + HTTP /health + RAG 抽样
#
#   bash deploy/verify-stack.sh
#   DEPLOY_PORT=8082 bash deploy/verify-stack.sh
# =============================================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/apps/agent-platform}"
DEPLOY_PORT="${DEPLOY_PORT:-8082}"
COMPOSE_BASE="deploy/docker-compose.prod.yml"
COMPOSE_MYSQL="deploy/docker-compose.prod.external-mysql.yml"
COMPOSE_FILE_ARGS=(-f "${COMPOSE_BASE}")

cd "${APP_DIR}" || { echo "[ERROR] ${APP_DIR} not found"; exit 1; }

[[ -f .env ]] && DEPLOY_PORT="$(grep '^DEPLOY_PORT=' .env | cut -d= -f2- || echo "${DEPLOY_PORT}")"
[[ -f .env ]] && grep -q '^MYSQL_DOCKER_NETWORK=' .env && COMPOSE_FILE_ARGS+=(-f "${COMPOSE_MYSQL}")

compose() { docker compose "${COMPOSE_FILE_ARGS[@]}" --project-directory . "$@"; }

echo "== Docker 容器状态 =="
compose ps redis chromadb neo4j backend gateway 2>/dev/null || compose ps

REQUIRED=(agent-prod-redis agent-prod-chromadb agent-prod-neo4j agent-prod-backend agent-prod-gateway)
for c in "${REQUIRED[@]}"; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$c"; then
    echo "[FAIL] 容器未运行: $c"
    exit 1
  fi
  st=$(docker inspect --format='{{.State.Status}}' "$c")
  echo "  OK  $c ($st)"
done

echo ""
echo "== HTTP /health =="
curl -sf "http://127.0.0.1:${DEPLOY_PORT}/health" | python3 -m json.tool || {
  echo "[FAIL] /health 不可达 (port ${DEPLOY_PORT})"
  exit 1
}

echo ""
echo "== RAG 验证 =="
SKIP_SEED=1 bash "${APP_DIR}/deploy/post-deploy-rag.sh"

echo ""
echo "[ALL OK] 栈验证通过"

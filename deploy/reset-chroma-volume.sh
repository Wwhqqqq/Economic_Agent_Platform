#!/usr/bin/env bash
# =============================================================================
# 重置 ChromaDB 持久化数据（修复 KeyError _type / 版本不兼容）
#
# 会清空 data/docker/chroma 并重启 chromadb 容器。
# 灌库前若 RAG 报 Chroma 错误，先执行本脚本再 post-deploy-rag.sh
#
#   bash deploy/reset-chroma-volume.sh
# =============================================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/apps/agent-platform}"
COMPOSE_BASE="deploy/docker-compose.prod.yml"
COMPOSE_MYSQL="deploy/docker-compose.prod.external-mysql.yml"
COMPOSE_FILE_ARGS=(-f "${COMPOSE_BASE}")

cd "${APP_DIR}" || exit 1

if [[ -f .env ]] && grep -q '^MYSQL_DOCKER_NETWORK=' .env; then
  COMPOSE_FILE_ARGS+=(-f "${COMPOSE_MYSQL}")
fi

compose() {
  docker compose "${COMPOSE_FILE_ARGS[@]}" --project-directory . "$@"
}

CHROMA_DIR="${APP_DIR}/data/docker/chroma"
BACKUP_DIR="${APP_DIR}/data/docker/chroma.backup.$(date +%Y%m%d%H%M%S)"

echo "== 停止 ChromaDB 容器 =="
compose stop chromadb 2>/dev/null || true

if [[ -d "${CHROMA_DIR}" ]] && [[ -n "$(ls -A "${CHROMA_DIR}" 2>/dev/null || true)" ]]; then
  echo "== 备份旧数据到 ${BACKUP_DIR} =="
  cp -a "${CHROMA_DIR}" "${BACKUP_DIR}"
  echo "== 清空 Chroma 数据目录 =="
  rm -rf "${CHROMA_DIR:?}"/*
fi

mkdir -p "${CHROMA_DIR}"

echo "== 启动 ChromaDB =="
compose up -d chromadb

echo "== 等待 Chroma 就绪 =="
for i in $(seq 1 30); do
  if docker exec agent-prod-chromadb curl -sf http://localhost:8000/api/v1/heartbeat >/dev/null 2>&1; then
    echo "ChromaDB heartbeat OK"
    exit 0
  fi
  sleep 2
done

echo "[WARN] heartbeat 超时，请检查: docker logs agent-prod-chromadb --tail=50"
exit 1

#!/usr/bin/env bash
# =============================================================================
# Agent Platform — 增量更新部署（腾讯云，已有生产环境）
#
# 适用：服务器上已跑通过 one-click-deploy.sh 的实例，仅拉代码 + 迁移 + 重建应用层
# 不重建：Redis / Chroma / Neo4j（除非镜像版本变更需手动处理）
# 保留：已有 .env（不会覆盖 JWT、SMTP、API Key 等）
#
# 用法（SSH 登录服务器后）:
#   cd /opt/apps/agent-platform
#   bash deploy/incremental-update.sh
#
# 可选环境变量（与 one-click-deploy 相同）:
#   export MYSQL_CONTAINER=xxx
#   export DEEPSEEK_API_KEY=sk-xxx
#   export DEPLOY_PORT=8082
# =============================================================================

set -euo pipefail

APP_NAME="${APP_NAME:-agent-platform}"
APP_DIR="${APP_DIR:-/opt/apps/${APP_NAME}}"
GIT_BRANCH="${GIT_BRANCH:-main}"
REPO_URL="${REPO_URL:-https://github.com/Wwhqqqq/Economic_Agent_Platform.git}"
DEPLOY_PORT="${DEPLOY_PORT:-8082}"
SERVER_IP="${SERVER_IP:-111.229.87.157}"

MYSQL_CONTAINER="${MYSQL_CONTAINER:-}"
MYSQL_DOCKER_NETWORK="${MYSQL_DOCKER_NETWORK:-}"
MYSQL_HOST="${MYSQL_HOST:-}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-agent_platform}"

COMPOSE_BASE="deploy/docker-compose.prod.yml"
COMPOSE_MYSQL="deploy/docker-compose.prod.external-mysql.yml"
COMPOSE_FILE_ARGS=()
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-180}"
SKIP_GIT="${SKIP_GIT:-0}"
SERVICES="${SERVICES:-migrate,backend,gateway}"

STEP=0
log()  { STEP=$((STEP + 1)); echo ""; echo "== [${STEP}] $*"; }
info() { echo "    $*"; }
die()  { echo ""; echo "[ERROR] $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1"
}

set_env_var() {
  local key="$1" val="$2" file="${3:-.env}"
  if [[ -f "$file" ]] && grep -q "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$file"
  else
    echo "${key}=${val}" >> "$file"
  fi
}

load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue
    local key="${line%%=*}"
    local val="${line#*=}"
    case "$key" in
      MYSQL_CONTAINER) [[ -z "${MYSQL_CONTAINER}" ]] && MYSQL_CONTAINER="$val" ;;
      MYSQL_DOCKER_NETWORK) [[ -z "${MYSQL_DOCKER_NETWORK}" ]] && MYSQL_DOCKER_NETWORK="$val" ;;
      MYSQL_HOST) [[ -z "${MYSQL_HOST}" ]] && MYSQL_HOST="$val" ;;
      MYSQL_PORT) [[ -z "${MYSQL_PORT}" || "${MYSQL_PORT}" == "3306" ]] && MYSQL_PORT="$val" ;;
      MYSQL_USER) [[ -z "${MYSQL_USER}" || "${MYSQL_USER}" == "root" ]] && MYSQL_USER="$val" ;;
      MYSQL_PASSWORD) [[ -z "${MYSQL_PASSWORD}" ]] && MYSQL_PASSWORD="$val" ;;
      MYSQL_DATABASE) [[ -z "${MYSQL_DATABASE}" || "${MYSQL_DATABASE}" == "agent_platform" ]] && MYSQL_DATABASE="$val" ;;
      DEPLOY_PORT) DEPLOY_PORT="$val" ;;
    esac
  done < "$file"
}

append_missing_env_keys() {
  local template="deploy/env.production.template"
  [[ -f "$template" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue
    local key="${line%%=*}"
    grep -q "^${key}=" .env 2>/dev/null || echo "$line" >> .env
  done < "$template"
  info "已补齐 .env 中缺失的新配置项（不覆盖已有值）"
}

setup_compose_files() {
  COMPOSE_FILE_ARGS=(-f "${COMPOSE_BASE}")
  if [[ -n "${MYSQL_DOCKER_NETWORK:-}" ]]; then
    COMPOSE_FILE_ARGS+=(-f "${COMPOSE_MYSQL}")
  fi
}

compose() {
  docker compose "${COMPOSE_FILE_ARGS[@]}" --project-directory . "$@"
}

detect_mysql_container() {
  [[ -n "${MYSQL_CONTAINER}" ]] && return 0
  info "自动探测 MySQL 容器..."
  local line name image
  while IFS= read -r line; do
    name="${line%%$'\t'*}"
    image="${line#*$'\t'}"
    [[ "${name}" == agent-prod-* ]] && continue
    if echo "${image} ${name}" | grep -qiE 'mysql|mariadb'; then
      MYSQL_CONTAINER="${name}"
      info "探测到 MySQL 容器: ${MYSQL_CONTAINER}"
      return 0
    fi
  done < <(docker ps --format '{{.Names}}\t{{.Image}}')
  die "未找到 MySQL 容器，请 export MYSQL_CONTAINER=容器名"
}

detect_mysql_network() {
  [[ -n "${MYSQL_DOCKER_NETWORK}" ]] && return 0
  local networks net
  networks=$(docker inspect "${MYSQL_CONTAINER}" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}')
  for net in ${networks}; do
    case "${net}" in
      bridge|host|none) continue ;;
      agent-platform-prod_*|agent-platform-prod-*) continue ;;
    esac
    MYSQL_DOCKER_NETWORK="${net}"
    info "探测到 MySQL 网络: ${MYSQL_DOCKER_NETWORK}"
    return 0
  done
  for net in ${networks}; do
    [[ "${net}" != "bridge" ]] && MYSQL_DOCKER_NETWORK="${net}" && return 0
  done
  MYSQL_DOCKER_NETWORK="bridge"
}

wait_for_health() {
  local url="http://127.0.0.1:${DEPLOY_PORT}/health"
  local elapsed=0
  info "等待服务就绪: ${url}"
  while (( elapsed < HEALTH_TIMEOUT )); do
    if curl -sf "$url" >/dev/null 2>&1; then
      curl -sf "$url" | head -c 400 || true
      echo ""
      info "健康检查通过"
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done
  die "健康检查超时，请执行: compose logs backend gateway --tail=80"
}

# ---------- 开始 ----------
log "增量更新 — 前置检查"

require_cmd git
require_cmd docker
require_cmd curl
docker compose version >/dev/null 2>&1 || die "需要 Docker Compose v2"

[[ -d "${APP_DIR}/.git" ]] || die "未找到已部署仓库 ${APP_DIR}，请先运行 deploy/one-click-deploy.sh"
[[ -f "${APP_DIR}/.env" ]] || die "未找到 ${APP_DIR}/.env，请先完成首次部署"

cd "${APP_DIR}"
load_env_file ".env"

detect_mysql_container
detect_mysql_network
MYSQL_HOST="${MYSQL_HOST:-${MYSQL_CONTAINER}}"
[[ -n "${MYSQL_PASSWORD}" ]] || die "MYSQL_PASSWORD 为空，请检查 .env"

info "目录     : ${APP_DIR}"
info "分支     : ${GIT_BRANCH}"
info "端口     : ${DEPLOY_PORT}"
info "MySQL    : ${MYSQL_CONTAINER} @ ${MYSQL_DOCKER_NETWORK}"

# ---------- 拉代码 ----------
if [[ "${SKIP_GIT}" != "1" ]]; then
  log "拉取最新 ${GIT_BRANCH}"
  OLD_HEAD="$(git rev-parse --short HEAD)"
  git remote set-url origin "${REPO_URL}"
  git fetch origin "${GIT_BRANCH}"
  git checkout "${GIT_BRANCH}"
  git reset --hard "origin/${GIT_BRANCH}"
  NEW_HEAD="$(git rev-parse --short HEAD)"
  info "${OLD_HEAD} -> ${NEW_HEAD}  $(git log -1 --pretty=format:'%s')"
else
  log "跳过 Git 拉取 (SKIP_GIT=1)"
  NEW_HEAD="$(git rev-parse --short HEAD)"
fi

[[ -f "${COMPOSE_BASE}" ]] || die "缺少 ${COMPOSE_BASE}"

# ---------- 同步 .env 连接项（不覆盖密钥） ----------
log "校验 .env"

append_missing_env_keys

DB_URL="mysql+aiomysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}?charset=utf8mb4"
set_env_var DEPLOY_PORT "${DEPLOY_PORT}"
set_env_var MYSQL_CONTAINER "${MYSQL_CONTAINER}"
set_env_var MYSQL_DOCKER_NETWORK "${MYSQL_DOCKER_NETWORK}"
set_env_var MYSQL_HOST "${MYSQL_HOST}"
set_env_var MYSQL_PORT "${MYSQL_PORT}"
set_env_var MYSQL_USER "${MYSQL_USER}"
set_env_var MYSQL_PASSWORD "${MYSQL_PASSWORD}"
set_env_var MYSQL_DATABASE "${MYSQL_DATABASE}"
set_env_var DATABASE_URL "${DB_URL}"

if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  set_env_var DEEPSEEK_API_KEY "${DEEPSEEK_API_KEY}"
  info "已更新 DEEPSEEK_API_KEY"
fi

setup_compose_files
export DEPLOY_PORT MYSQL_CONTAINER MYSQL_DOCKER_NETWORK MYSQL_HOST MYSQL_PORT MYSQL_USER MYSQL_PASSWORD MYSQL_DATABASE

# ---------- 构建应用层镜像 ----------
log "构建镜像: ${SERVICES}"

IFS=',' read -ra BUILD_LIST <<< "${SERVICES}"
for svc in "${BUILD_LIST[@]}"; do
  svc="$(echo "$svc" | xargs)"
  [[ -n "$svc" ]] && compose build "$svc"
done

# ---------- 数据库迁移 ----------
log "Alembic 迁移 (upgrade head)"

compose run --rm migrate
info "迁移完成"

# ---------- 滚动更新 backend + gateway ----------
log "重启应用容器 (backend, gateway)"

compose up -d --no-deps --force-recreate backend
compose up -d --no-deps --force-recreate gateway

info "容器状态:"
compose ps migrate backend gateway redis chromadb neo4j 2>/dev/null || compose ps

# ---------- 健康检查 ----------
log "健康检查"
wait_for_health

# ---------- 完成 ----------
log "增量更新完成"

echo ""
echo "  访问     : http://${SERVER_IP}:${DEPLOY_PORT}"
echo "  版本     : ${GIT_BRANCH} @ ${NEW_HEAD}"
echo "  日志     : cd ${APP_DIR} && docker compose -f ${COMPOSE_BASE} -f ${COMPOSE_MYSQL} --project-directory . logs -f backend"
echo ""
echo "  下次更新 : bash ${APP_DIR}/deploy/incremental-update.sh"
echo ""

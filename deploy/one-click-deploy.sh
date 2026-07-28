#!/usr/bin/env bash
# =============================================================================
# Agent Platform — 一键部署脚本（腾讯云服务器）
#
# 功能：克隆/更新 main 分支 → 建库 → Docker 构建 → Alembic 迁移 → 健康检查
# 约定：复用已有 Docker MySQL 容器；对外端口 8082（避开 8080）；不影响本地开发
#
# 用法（在服务器上执行）:
#   export DEEPSEEK_API_KEY="sk-xxxx"    # 可选
#   bash deploy/one-click-deploy.sh
#
# 若服务器上有多个 MySQL 容器，请手动指定:
#   export MYSQL_CONTAINER="你的mysql容器名"
#   bash deploy/one-click-deploy.sh
# =============================================================================

set -euo pipefail

# ---------- 可配置项 ----------
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
MYSQL_PASSWORD="${MYSQL_PASSWORD:-whq050207}"
MYSQL_DATABASE="${MYSQL_DATABASE:-agent_platform}"

COMPOSE_BASE="deploy/docker-compose.prod.yml"
COMPOSE_MYSQL="deploy/docker-compose.prod.external-mysql.yml"
COMPOSE_FILE_ARGS=()
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"

# ---------- 工具函数 ----------
STEP=0
log()  { STEP=$((STEP + 1)); echo ""; echo "== [${STEP}] $*"; }
info() { echo "    $*"; }
die()  { echo ""; echo "[ERROR] $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1，请先安装"
}

set_env_var() {
  local key="$1" val="$2" file="${3:-.env}"
  if [[ -f "$file" ]] && grep -q "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$file"
  else
    echo "${key}=${val}" >> "$file"
  fi
}

wait_for_health() {
  local url="http://127.0.0.1:${DEPLOY_PORT}/health"
  local elapsed=0
  info "等待服务就绪: ${url}"
  while (( elapsed < HEALTH_TIMEOUT )); do
    if curl -sf "$url" >/dev/null 2>&1; then
      info "健康检查通过"
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done
  die "健康检查超时（${HEALTH_TIMEOUT}s），请查看日志: compose logs"
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

  die "未找到运行中的 MySQL 容器。请设置: export MYSQL_CONTAINER=容器名"
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
  info "使用默认 bridge 网络"
}

create_mysql_database() {
  local sql="CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

  info "在容器 ${MYSQL_CONTAINER} 中创建数据库 ${MYSQL_DATABASE} ..."
  docker exec "${MYSQL_CONTAINER}" \
    mysql -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" \
    -e "${sql}" \
    || die "无法连接 Docker MySQL 容器 ${MYSQL_CONTAINER}，请检查 MYSQL_USER / MYSQL_PASSWORD"
  info "数据库 ${MYSQL_DATABASE} 已就绪"
}

# ---------- 前置检查 ----------
log "前置检查"

require_cmd git
require_cmd docker
require_cmd curl

docker compose version >/dev/null 2>&1 || die "需要 Docker Compose v2（docker compose）"
[[ "${DEPLOY_PORT}" != "8080" ]] || die "端口 8080 已被其他项目占用，请使用 DEPLOY_PORT=8082"

detect_mysql_container
detect_mysql_network
MYSQL_HOST="${MYSQL_HOST:-${MYSQL_CONTAINER}}"

info "部署目录 : ${APP_DIR}"
info "Git 分支 : ${GIT_BRANCH}"
info "访问端口 : ${DEPLOY_PORT}"
info "MySQL 容器: ${MYSQL_CONTAINER}"
info "MySQL 网络: ${MYSQL_DOCKER_NETWORK}"
info "连接地址 : ${MYSQL_USER}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}"

# ---------- 拉取 main 分支 ----------
log "拉取 ${GIT_BRANCH} 分支代码"

mkdir -p "$(dirname "${APP_DIR}")"

if [[ -d "${APP_DIR}/.git" ]]; then
  info "仓库已存在，更新到 origin/${GIT_BRANCH} ..."
  git -C "${APP_DIR}" remote set-url origin "${REPO_URL}"
  git -C "${APP_DIR}" fetch origin "${GIT_BRANCH}"
  git -C "${APP_DIR}" checkout "${GIT_BRANCH}"
  git -C "${APP_DIR}" reset --hard "origin/${GIT_BRANCH}"
  info "当前版本: $(git -C "${APP_DIR}" rev-parse --short HEAD) $(git -C "${APP_DIR}" log -1 --pretty=format:'%s')"
else
  info "首次克隆 ${REPO_URL} (${GIT_BRANCH}) ..."
  git clone --branch "${GIT_BRANCH}" --single-branch "${REPO_URL}" "${APP_DIR}"
  info "当前版本: $(git -C "${APP_DIR}" rev-parse --short HEAD)"
fi

cd "${APP_DIR}"

[[ -f "${COMPOSE_BASE}" ]] || die "未找到 ${COMPOSE_BASE}，请确认 main 分支已包含 deploy 目录"

# ---------- 配置 .env ----------
log "配置生产环境 .env"

if [[ ! -f .env ]]; then
  cp deploy/env.production.template .env
  JWT_SECRET="$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')"
  NEO4J_PASS="$(openssl rand -hex 16 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(16))')"
  sed -i "s/CHANGE_ME_JWT_SECRET/${JWT_SECRET}/" .env
  sed -i "s/prod_neo4j_password_change_me/${NEO4J_PASS}/" .env
  info "已创建 .env 并生成 JWT_SECRET / NEO4J_PASSWORD"
else
  info "沿用已有 .env"
fi

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
  info "已写入 DEEPSEEK_API_KEY"
elif ! grep -q "^DEEPSEEK_API_KEY=.\+" .env 2>/dev/null; then
  info "提示: 未设置 DEEPSEEK_API_KEY，LLM 不可用。可 export DEEPSEEK_API_KEY=sk-xxx 后重新运行"
fi

# ---------- 建库 & 数据目录 ----------
log "初始化数据目录与 MySQL 数据库"

mkdir -p data/docker/redis data/docker/chroma \
         data/docker/neo4j/data data/docker/neo4j/logs data/chroma

create_mysql_database

# ---------- Docker 构建 & 启动 ----------
log "Docker 构建并启动（加入 MySQL 网络 + Alembic 迁移）"

setup_compose_files
export DEPLOY_PORT MYSQL_CONTAINER MYSQL_DOCKER_NETWORK MYSQL_HOST MYSQL_PORT MYSQL_USER MYSQL_PASSWORD MYSQL_DATABASE

compose up -d --build

info "容器状态:"
compose ps

# ---------- 健康检查 ----------
log "健康检查"
wait_for_health

# ---------- 完成 ----------
log "部署完成"

echo ""
echo "  访问地址 : http://${SERVER_IP}:${DEPLOY_PORT}"
echo "  健康检查 : curl http://${SERVER_IP}:${DEPLOY_PORT}/health"
echo "  Git 分支 : ${GIT_BRANCH} @ $(git rev-parse --short HEAD)"
echo "  MySQL    : 复用容器 ${MYSQL_CONTAINER}（网络 ${MYSQL_DOCKER_NETWORK}）"
echo ""
echo "  常用命令:"
echo "    cd ${APP_DIR}"
echo "    docker compose -f deploy/docker-compose.prod.yml -f deploy/docker-compose.prod.external-mysql.yml --project-directory . logs -f"
echo "    docker compose -f deploy/docker-compose.prod.yml -f deploy/docker-compose.prod.external-mysql.yml --project-directory . restart backend"
echo "    docker compose -f deploy/docker-compose.prod.yml -f deploy/docker-compose.prod.external-mysql.yml --project-directory . run --rm migrate"
echo "    docker compose -f deploy/docker-compose.prod.yml -f deploy/docker-compose.prod.external-mysql.yml --project-directory . down"
echo ""
echo "  更新部署:"
echo "    bash ${APP_DIR}/deploy/one-click-deploy.sh"
echo ""

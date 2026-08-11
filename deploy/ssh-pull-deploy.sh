#!/usr/bin/env bash
# =============================================================================
# Agent Platform — SSH 拉取 + 增量部署（腾讯云 / Linux 服务器）
#
# 使用 GitHub SSH 地址拉代码，适合已在服务器配置 deploy key 或 SSH 公钥的场景。
#
# 【服务器一次性准备 — SSH 拉 GitHub】
#   1. 生成密钥（若无）:
#        ssh-keygen -t ed25519 -C "agent-platform-deploy" -f ~/.ssh/id_ed25519_github -N ""
#   2. 查看公钥并添加到 GitHub → Settings → SSH and GPG keys:
#        cat ~/.ssh/id_ed25519_github.pub
#   3. 配置 ~/.ssh/config:
#        Host github.com
#          HostName github.com
#          User git
#          IdentityFile ~/.ssh/id_ed25519_github
#          IdentitiesOnly yes
#   4. 测试:
#        ssh -T git@github.com
#
# 【首次部署】
#   export DEEPSEEK_API_KEY="sk-xxx"          # 可选
#   export MYSQL_PASSWORD="your-mysql-pass"   # 必填（若与默认不同）
#   bash deploy/ssh-pull-deploy.sh --first
#
# 【日常更新（推荐）】
#   cd /opt/apps/agent-platform
#   bash deploy/ssh-pull-deploy.sh
#
# 环境变量:
#   REPO_SSH_URL   默认 git@github.com:Wwhqqqq/Economic_Agent_Platform.git
#   GIT_BRANCH     默认 main
#   APP_DIR        默认 /opt/apps/agent-platform
#   DEPLOY_PORT    默认 8082
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REPO_SSH_URL="${REPO_SSH_URL:-git@github.com:Wwhqqqq/Economic_Agent_Platform.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/apps/agent-platform}"
MODE="${1:-update}"

log() { echo ""; echo "== $*"; }
info() { echo "    $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

ensure_github_ssh() {
  if ssh -o BatchMode=yes -o ConnectTimeout=10 -T git@github.com 2>&1 | grep -qi "successfully authenticated"; then
    info "GitHub SSH 认证正常"
    return 0
  fi
  info "警告: GitHub SSH 未通过 BatchMode 测试，继续尝试 git 操作…"
  info "若 clone/fetch 失败，请按脚本头部说明配置 ~/.ssh/config 与 deploy key"
}

clone_or_update_repo() {
  if [[ -d "${APP_DIR}/.git" ]]; then
    log "SSH 拉取最新代码 → ${GIT_BRANCH}"
    git -C "${APP_DIR}" remote set-url origin "${REPO_SSH_URL}"
    OLD="$(git -C "${APP_DIR}" rev-parse --short HEAD)"
    git -C "${APP_DIR}" fetch origin "${GIT_BRANCH}"
    git -C "${APP_DIR}" checkout "${GIT_BRANCH}"
    git -C "${APP_DIR}" reset --hard "origin/${GIT_BRANCH}"
    NEW="$(git -C "${APP_DIR}" rev-parse --short HEAD)"
    info "${OLD} -> ${NEW}  $(git -C "${APP_DIR}" log -1 --pretty=format:'%s')"
  else
    log "SSH 首次克隆 ${REPO_SSH_URL}"
    mkdir -p "$(dirname "${APP_DIR}")"
    git clone --branch "${GIT_BRANCH}" --single-branch "${REPO_SSH_URL}" "${APP_DIR}"
    info "当前版本: $(git -C "${APP_DIR}" rev-parse --short HEAD)"
  fi
}

run_incremental_update() {
  export REPO_URL="${REPO_SSH_URL}"
  export GIT_BRANCH
  export APP_DIR
  bash "${APP_DIR}/deploy/incremental-update.sh"
}

run_first_deploy() {
  export REPO_URL="${REPO_SSH_URL}"
  export GIT_BRANCH
  export APP_DIR
  bash "${APP_DIR}/deploy/one-click-deploy.sh"
}

# ---------- 从本机仓库目录执行时：先同步到 APP_DIR ----------
if [[ "${MODE}" == "--local-sync" ]]; then
  # 开发机测试用：不 SSH，仅把当前目录当作 APP_DIR 跑增量
  APP_DIR="${REPO_ROOT}"
  export REPO_URL="${REPO_SSH_URL}"
  export APP_DIR
  bash "${SCRIPT_DIR}/incremental-update.sh"
  exit 0
fi

ensure_github_ssh

case "${MODE}" in
  --first|first)
    clone_or_update_repo
    run_first_deploy
    ;;
  --update|update|"")
    [[ -d "${APP_DIR}/.git" ]] || die "未找到 ${APP_DIR}，请先运行: bash deploy/ssh-pull-deploy.sh --first"
    clone_or_update_repo
    run_incremental_update
    ;;
  --pull-only|pull-only)
    clone_or_update_repo
    info "仅拉代码，未重启服务"
    ;;
  *)
    die "未知参数: ${MODE}  用法: [--first|--update|--pull-only]"
    ;;
esac

log "完成"
info "仓库 SSH : ${REPO_SSH_URL}"
info "部署目录 : ${APP_DIR}"
info "分支     : ${GIT_BRANCH}"

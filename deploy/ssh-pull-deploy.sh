#!/usr/bin/env bash
# =============================================================================
# Agent Platform — SSH 拉取 + 增量部署（腾讯云 / Linux 服务器）
#
# 已绑定 GitHub Deploy Key: PlatformAgent（Read/write）
# 仓库 SSH: git@github.com:Wwhqqqq/Economic_Agent_Platform.git
#
# 【服务器 ~/.ssh/config 示例 — 指向已有 PlatformAgent 私钥】
#   Host github.com
#     HostName github.com
#     User git
#     IdentityFile ~/.ssh/platform_agent
#     IdentitiesOnly yes
#
# 若私钥路径不同，部署前 export:
#   export GITHUB_DEPLOY_KEY=/root/.ssh/你的PlatformAgent私钥路径
#
# 【日常更新（推荐）】
#   cd /opt/apps/agent-platform
#   bash deploy/ssh-pull-deploy.sh
#
# 【首次部署】
#   export MYSQL_PASSWORD="your-mysql-pass"
#   bash deploy/ssh-pull-deploy.sh --first
#
# 环境变量:
#   GITHUB_DEPLOY_KEY  PlatformAgent 私钥路径（自动探测见 setup_git_ssh）
#   REPO_SSH_URL       默认 git@github.com:Wwhqqqq/Economic_Agent_Platform.git
#   GIT_BRANCH         默认 main
#   APP_DIR            默认 /opt/apps/agent-platform
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REPO_SSH_URL="${REPO_SSH_URL:-git@github.com:Wwhqqqq/Economic_Agent_Platform.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/apps/agent-platform}"
MODE="${1:-update}"

# PlatformAgent 私钥常见路径（按优先级自动探测）
PLATFORM_AGENT_KEY_CANDIDATES=(
  "${GITHUB_DEPLOY_KEY:-}"
  "${HOME}/.ssh/platform_agent"
  "${HOME}/.ssh/PlatformAgent"
  "${HOME}/.ssh/id_ed25519_platform"
  "${HOME}/.ssh/id_rsa_platform_agent"
)

log() { echo ""; echo "== $*"; }
info() { echo "    $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

setup_git_ssh() {
  local key=""
  for candidate in "${PLATFORM_AGENT_KEY_CANDIDATES[@]}"; do
    [[ -n "${candidate}" && -f "${candidate}" ]] || continue
    key="${candidate}"
    break
  done

  if [[ -n "${key}" ]]; then
    export GIT_SSH_COMMAND="ssh -i ${key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
    info "使用 PlatformAgent 密钥: ${key}"
    return 0
  fi

  # 未找到文件时依赖 ~/.ssh/config（用户可能已配置 PlatformAgent）
  info "未找到 PlatformAgent 私钥文件，使用系统默认 SSH 配置（~/.ssh/config）"
}

ensure_github_ssh() {
  setup_git_ssh
  if ssh -o BatchMode=yes -o ConnectTimeout=10 -T git@github.com 2>&1 | grep -qiE "successfully authenticated|You've successfully authenticated"; then
    info "GitHub SSH 认证正常（PlatformAgent）"
    return 0
  fi
  echo ""
  echo "[ERROR] GitHub SSH 认证失败。" >&2
  echo "  PlatformAgent 私钥尚未正确安装到本机。" >&2
  echo "  请先阅读: deploy/SSH-RECOVERY.md" >&2
  echo "  安装命令: bash deploy/install-platform-agent-key.sh /path/to/platform_agent" >&2
  echo "  切勿运行 ssh-keygen 覆盖已有密钥。" >&2
  exit 1
}

clone_or_update_repo() {
  setup_git_ssh
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
  setup_git_ssh
  bash "${APP_DIR}/deploy/incremental-update.sh"
}

run_first_deploy() {
  export REPO_URL="${REPO_SSH_URL}"
  export GIT_BRANCH
  export APP_DIR
  setup_git_ssh
  bash "${APP_DIR}/deploy/one-click-deploy.sh"
}

if [[ "${MODE}" == "--local-sync" ]]; then
  APP_DIR="${REPO_ROOT}"
  export REPO_URL="${REPO_SSH_URL}"
  export APP_DIR
  setup_git_ssh
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
info "Deploy Key : PlatformAgent"
info "仓库 SSH   : ${REPO_SSH_URL}"
info "部署目录   : ${APP_DIR}"
info "分支       : ${GIT_BRANCH}"

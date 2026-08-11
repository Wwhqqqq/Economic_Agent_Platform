# =============================================================================
# 从 Windows 本机 SSH 到腾讯云 → 服务器用 PlatformAgent 密钥拉 GitHub 并部署
#
# GitHub 已配置 Deploy Key: PlatformAgent (Read/write)
#
# 用法:
#   .\deploy\ssh-pull-deploy.ps1                  # 日常增量更新
#   .\deploy\ssh-pull-deploy.ps1 -First           # 首次部署
#   .\deploy\ssh-pull-deploy.ps1 -PullOnly        # 仅拉代码
#
# 若服务器私钥不在默认路径，SSH 登录后指定:
#   export GITHUB_DEPLOY_KEY=/root/.ssh/platform_agent
# =============================================================================

param(
    [string]$Server = "111.229.87.157",
    [string]$SshUser = "root",
    [int]$Port = 8082,
    [string]$Branch = "main",
    [string]$AppDir = "/opt/apps/agent-platform",
    [string]$GithubDeployKey = "",
    [switch]$First,
    [switch]$PullOnly
)

$ErrorActionPreference = "Stop"

$mode = "update"
if ($First) { $mode = "--first" }
if ($PullOnly) { $mode = "--pull-only" }

$extraEnv = @()
if ($env:DEEPSEEK_API_KEY) {
    $extraEnv += "export DEEPSEEK_API_KEY='$($env:DEEPSEEK_API_KEY)'"
}
if ($env:MYSQL_PASSWORD) {
    $extraEnv += "export MYSQL_PASSWORD='$($env:MYSQL_PASSWORD)'"
}
if ($env:MYSQL_CONTAINER) {
    $extraEnv += "export MYSQL_CONTAINER='$($env:MYSQL_CONTAINER)'"
}
$keyPath = if ($GithubDeployKey) { $GithubDeployKey } elseif ($env:GITHUB_DEPLOY_KEY) { $env:GITHUB_DEPLOY_KEY } else { "" }
if ($keyPath) {
    $extraEnv += "export GITHUB_DEPLOY_KEY='$keyPath'"
}

$remoteCmd = @"
set -e
export DEPLOY_PORT=$Port
export GIT_BRANCH='$Branch'
export APP_DIR='$AppDir'
export REPO_SSH_URL='git@github.com:Wwhqqqq/Economic_Agent_Platform.git'
export SERVER_IP='$Server'
$($extraEnv -join "`n")

if [ ! -f "`$APP_DIR/deploy/ssh-pull-deploy.sh" ]; then
  mkdir -p "`$(dirname `$APP_DIR)"
  if [ ! -d "`$APP_DIR/.git" ]; then
    # 首次克隆也走 PlatformAgent（setup_git_ssh 在脚本内处理）
    if [ -f "`$APP_DIR/../deploy/ssh-pull-deploy.sh" ]; then
      bash "`$APP_DIR/../deploy/ssh-pull-deploy.sh" --first
      exit 0
    fi
    git clone --branch $Branch --single-branch `$REPO_SSH_URL `$APP_DIR
  fi
fi

bash `$APP_DIR/deploy/ssh-pull-deploy.sh $mode
"@

Write-Host "SSH -> ${SshUser}@${Server}  Deploy Key: PlatformAgent  模式: $mode"
ssh "${SshUser}@${Server}" $remoteCmd
Write-Host ""
Write-Host "完成: http://${Server}:${Port}"

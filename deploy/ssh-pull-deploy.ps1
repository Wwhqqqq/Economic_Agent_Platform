# =============================================================================
# 从 Windows 本机 SSH 到腾讯云，触发服务器 SSH 拉取 + 增量部署
#
# 用法:
#   .\deploy\ssh-pull-deploy.ps1
#   .\deploy\ssh-pull-deploy.ps1 -First          # 服务器首次部署
#   .\deploy\ssh-pull-deploy.ps1 -PullOnly       # 仅拉代码
#
# 可选环境变量:
#   $env:DEEPSEEK_API_KEY = "sk-xxxx"
#   $env:MYSQL_PASSWORD = "your-pass"
# =============================================================================

param(
    [string]$Server = "111.229.87.157",
    [string]$SshUser = "root",
    [int]$Port = 8082,
    [string]$Branch = "main",
    [string]$AppDir = "/opt/apps/agent-platform",
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

$remoteCmd = @"
set -e
export DEPLOY_PORT=$Port
export GIT_BRANCH='$Branch'
export APP_DIR='$AppDir'
export REPO_SSH_URL='git@github.com:Wwhqqqq/Economic_Agent_Platform.git'
export SERVER_IP='$Server'
$($extraEnv -join "`n")

# 确保部署脚本存在（首次从 GitHub SSH 克隆最小骨架）
if [ ! -f "`$APP_DIR/deploy/ssh-pull-deploy.sh" ]; then
  mkdir -p "`$(dirname `$APP_DIR)"
  if [ ! -d "`$APP_DIR/.git" ]; then
    git clone --branch $Branch --single-branch `$REPO_SSH_URL `$APP_DIR
  fi
fi

bash `$APP_DIR/deploy/ssh-pull-deploy.sh $mode
"@

Write-Host "SSH → ${SshUser}@${Server}  模式: $mode  分支: $Branch"
ssh "${SshUser}@${Server}" $remoteCmd
Write-Host ""
Write-Host "完成: http://${Server}:${Port}"

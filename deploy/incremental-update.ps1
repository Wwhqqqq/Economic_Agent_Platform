# 从本机 SSH 到腾讯云，触发服务器上增量更新（不覆盖 .env 密钥）
#
# 用法:
#   .\deploy\incremental-update.ps1
#
# 可选:
#   $env:DEEPSEEK_API_KEY = "sk-xxxx"
#   $env:MYSQL_CONTAINER = "deploy-mysql-1"

param(
    [string]$Server = "111.229.87.157",
    [string]$SshUser = "ubuntu",
    [int]$Port = 8082,
    [string]$Branch = "main",
    [string]$AppDir = "/opt/apps/agent-platform",
    [string]$MysqlContainer = ""
)

$ErrorActionPreference = "Stop"

$deepseekLine = ""
if ($env:DEEPSEEK_API_KEY) {
    $deepseekLine = "export DEEPSEEK_API_KEY='$($env:DEEPSEEK_API_KEY)'"
}

$mysqlContainerLine = ""
if ($env:MYSQL_CONTAINER) {
    $mysqlContainerLine = "export MYSQL_CONTAINER='$($env:MYSQL_CONTAINER)'"
} elseif ($MysqlContainer) {
    $mysqlContainerLine = "export MYSQL_CONTAINER='$MysqlContainer'"
}

$remoteCmd = @"
set -e
export DEPLOY_PORT=$Port
export GIT_BRANCH='$Branch'
export SERVER_IP='$Server'
export APP_DIR='$AppDir'
$deepseekLine
$mysqlContainerLine

if [ ! -f "`$APP_DIR/deploy/incremental-update.sh" ]; then
  echo '未找到 incremental-update.sh，先拉取 main 获取 deploy 脚本...'
  git -C "`$APP_DIR" fetch origin main
  git -C "`$APP_DIR" checkout main
  git -C "`$APP_DIR" reset --hard origin/main
fi

bash `$APP_DIR/deploy/incremental-update.sh
"@

Write-Host "连接 ${SshUser}@${Server}，增量更新到端口 ${Port} ..."
ssh "${SshUser}@${Server}" $remoteCmd
Write-Host ""
Write-Host "完成: http://${Server}:${Port}/health"

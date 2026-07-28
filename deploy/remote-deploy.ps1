# 从本机 SSH 到腾讯云，触发服务器上一键部署（拉取 main 分支）
#
# 用法:
#   $env:DEEPSEEK_API_KEY = "sk-xxxx"   # 可选
#   $env:MYSQL_CONTAINER = "mysql"      # 可选，服务器有多个 MySQL 时指定
#   .\deploy\remote-deploy.ps1

param(
    [string]$Server = "111.229.87.157",
    [string]$SshUser = "root",
    [int]$Port = 8082,
    [string]$Branch = "main",
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
export MYSQL_PASSWORD='whq050207'
export MYSQL_USER='root'
export MYSQL_DATABASE='agent_platform'
export SERVER_IP='$Server'
$deepseekLine
$mysqlContainerLine

APP_DIR=/opt/apps/agent-platform
REPO=https://github.com/Wwhqqqq/Economic_Agent_Platform.git

if [ ! -f "`$APP_DIR/deploy/one-click-deploy.sh" ]; then
  mkdir -p /opt/apps
  git clone --branch $Branch --single-branch `$REPO `$APP_DIR
fi

bash `$APP_DIR/deploy/one-click-deploy.sh
"@

Write-Host "连接 ${SshUser}@${Server}，部署 main 分支到端口 ${Port} ..."
ssh "${SshUser}@${Server}" $remoteCmd
Write-Host ""
Write-Host "完成: http://${Server}:${Port}"

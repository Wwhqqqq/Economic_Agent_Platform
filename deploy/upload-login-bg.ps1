# 上传登录页背景资源到服务器并重建 gateway（仅前端静态资源变更时使用）
#
# 用法（需能 ssh ubuntu@111.229.87.157）:
#   .\deploy\upload-login-bg.ps1
#
# 可选:
#   .\deploy\upload-login-bg.ps1 -Server 111.229.87.157 -SshUser ubuntu

param(
    [string]$Server = "111.229.87.157",
    [string]$SshUser = "ubuntu",
    [string]$AppDir = "/opt/apps/agent-platform",
    [int]$Port = 8082
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$files = @(
    @{ Local = "$Root\frontend\public\images\login-bg-mint.png"; Remote = "$AppDir/frontend/public/images/login-bg-mint.png" },
    @{ Local = "$Root\frontend\public\images\login-bg-mint-rich.png"; Remote = "$AppDir/frontend/public/images/login-bg-mint-rich.png" },
    @{ Local = "$Root\frontend\src\views\LoginView.vue"; Remote = "$AppDir/frontend/src/views/LoginView.vue" }
)

foreach ($f in $files) {
    if (-not (Test-Path $f.Local)) {
        Write-Error "缺少文件: $($f.Local)"
    }
}

Write-Host "== 上传登录页资源到 ${SshUser}@${Server} =="
ssh "${SshUser}@${Server}" "mkdir -p ${AppDir}/frontend/public/images ${AppDir}/frontend/src/views"

foreach ($f in $files) {
    Write-Host "  -> $($f.Remote)"
    scp $f.Local "${SshUser}@${Server}:$($f.Remote)"
}

$remoteCmd = @"
set -e
cd '$AppDir'
export SKIP_GIT=1
export SERVICES=gateway
export DEPLOY_PORT=$Port
bash deploy/incremental-update.sh
"@

Write-Host ""
Write-Host "== 重建 gateway 并健康检查 =="
ssh "${SshUser}@${Server}" $remoteCmd

Write-Host ""
Write-Host "完成: http://${Server}:${Port}"

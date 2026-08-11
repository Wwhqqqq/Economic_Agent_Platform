# =============================================================================
# 从 Windows 上传 PlatformAgent 私钥到服务器（不生成新密钥）
#
# 用法:
#   .\deploy\install-platform-agent-key.ps1 -KeyPath "C:\Users\666\.ssh\platform_agent"
#
# 前提: 仍能 ssh root@111.229.87.157 登录（密码或现有服务器密钥）
# =============================================================================

param(
    [Parameter(Mandatory = $true)]
    [string]$KeyPath,
    [string]$Server = "111.229.87.157",
    [string]$SshUser = "root",
    [string]$RemotePath = "/root/.ssh/platform_agent"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $KeyPath)) {
    Write-Error "找不到私钥文件: $KeyPath"
}

Write-Host "上传 PlatformAgent 私钥 -> ${SshUser}@${Server}:${RemotePath}"
scp $KeyPath "${SshUser}@${Server}:${RemotePath}"

$remoteCmd = @"
chmod 600 ${RemotePath}
mkdir -p ~/.ssh && chmod 700 ~/.ssh
if ! grep -q 'Host github.com' ~/.ssh/config 2>/dev/null; then
  cat >> ~/.ssh/config <<'EOF'

Host github.com
  HostName github.com
  User git
  IdentityFile ${RemotePath}
  IdentitiesOnly yes
EOF
  chmod 600 ~/.ssh/config
fi
echo '--- 测试 GitHub ---'
ssh -T git@github.com || true
echo '--- 公钥指纹（应对齐 GitHub PlatformAgent）---'
ssh-keygen -y -f ${RemotePath} | ssh-keygen -lf -
"@

ssh "${SshUser}@${Server}" $remoteCmd
Write-Host ""
Write-Host "完成。若 GitHub 测试通过，在服务器执行:"
Write-Host "  bash /opt/apps/agent-platform/deploy/ssh-pull-deploy.sh"

#!/usr/bin/env bash
# =============================================================================
# 将【已有的】PlatformAgent 私钥安装到服务器 — 绝不生成新密钥
#
# 用法（在服务器上，已通过腾讯云控制台登录）:
#   bash deploy/install-platform-agent-key.sh /path/to/platform_agent_private_key
#
# 或从本机 SCP 上传后:
#   scp C:\Users\你\.ssh\platform_agent root@111.229.87.157:/root/.ssh/platform_agent
#   ssh root@111.229.87.157 "bash /opt/apps/agent-platform/deploy/install-platform-agent-key.sh /root/.ssh/platform_agent"
# =============================================================================

set -euo pipefail

KEY_SRC="${1:-}"
KEY_DEST="${HOME}/.ssh/platform_agent"
CONFIG="${HOME}/.ssh/config"

die() { echo "[ERROR] $*" >&2; exit 1; }

[[ -n "${KEY_SRC}" ]] || die "用法: $0 /path/to/PlatformAgent私钥文件"
[[ -f "${KEY_SRC}" ]] || die "找不到私钥文件: ${KEY_SRC}"

mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"

cp "${KEY_SRC}" "${KEY_DEST}"
chmod 600 "${KEY_DEST}"

# 备份已有 config
if [[ -f "${CONFIG}" ]]; then
  cp "${CONFIG}" "${CONFIG}.bak.$(date +%Y%m%d%H%M%S)"
fi

# 写入 github.com 段（若已有则追加 IdentityFile 提示）
if [[ -f "${CONFIG}" ]] && grep -q "^Host github.com" "${CONFIG}"; then
  echo "    已存在 Host github.com，请手动确认 IdentityFile 指向: ${KEY_DEST}"
else
  cat >> "${CONFIG}" <<EOF

Host github.com
  HostName github.com
  User git
  IdentityFile ${KEY_DEST}
  IdentitiesOnly yes
EOF
  chmod 600 "${CONFIG}"
fi

echo ""
echo "私钥已安装: ${KEY_DEST}"
echo "测试 GitHub SSH:"
ssh -T git@github.com || true
echo ""
echo "指纹应与 GitHub Deploy Key「PlatformAgent」一致:"
ssh-keygen -lf "${KEY_DEST}.pub" 2>/dev/null || ssh-keygen -y -f "${KEY_DEST}" | ssh-keygen -lf -
echo ""
echo "通过后执行: bash /opt/apps/agent-platform/deploy/ssh-pull-deploy.sh"

# SSH 密钥恢复指南 — PlatformAgent

> **重要**：部署脚本**不会**也**不应**自动生成 GitHub 密钥。  
> 若按旧文档执行了 `ssh-keygen`，可能覆盖了与 GitHub 上「PlatformAgent」配对的私钥。

GitHub 上已有 Deploy Key：

- 名称：**PlatformAgent**
- 指纹：`SHA256:9OeCohcTQaC3Jze24QEm67SeFtAja2UsODj/O3d+mV8`
- 权限：Read/write

---

## 先确认：你「访问不到」的是哪一种？

| 现象 | 原因 | 看下面章节 |
|------|------|------------|
| `ssh root@111.229.87.157` 失败 | 服务器 SSH 登录问题 | §A |
| 能登录服务器，但 `git fetch` / `ssh -T git@github.com` 失败 | PlatformAgent 私钥未装或装错 | §B |

---

## §A 无法登录腾讯云服务器

1. 打开 [腾讯云控制台](https://console.cloud.tencent.com/) → 云服务器 CVM → 你的实例  
2. 点击 **登录** → **标准登录方式 / OrcaTerm**（网页终端，不依赖本机 SSH 密钥）  
3. 用 root + 密码登录（购买实例时设置的，或在控制台重置密码）

---

## §B 恢复 GitHub PlatformAgent（推荐流程）

### 情况 1：你还保留着 PlatformAgent 私钥文件（最好）

私钥通常是创建 Deploy Key 时保存的文件，**没有** `.pub` 也行。

**在 Windows 上找私钥**（常见位置）：

- `C:\Users\666\.ssh\platform_agent`
- 下载目录、桌面、密码管理器导出、创建密钥时的备份

找到后，在 **本机 PowerShell** 执行：

```powershell
cd E:\Desktop\agent-platform\agent-platform

# 把路径改成你真实的私钥文件
.\deploy\install-platform-agent-key.ps1 -KeyPath "C:\Users\666\.ssh\platform_agent"
```

若无法用 scp，用 **腾讯云网页终端** 手动粘贴：

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
nano ~/.ssh/platform_agent   # 粘贴私钥全文，保存
chmod 600 ~/.ssh/platform_agent

cat >> ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/platform_agent
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config

ssh -T git@github.com
# 期望: Hi Wwhqqqq/Economic_Agent_Platform! You've successfully authenticated...

# 验证指纹与 GitHub 一致
ssh-keygen -y -f ~/.ssh/platform_agent | ssh-keygen -lf -
# 应包含 9OeCohcTQaC3Jze24QEm67SeFtAja2UsODj/O3d+mV8
```

通过后部署：

```bash
cd /opt/apps/agent-platform
bash deploy/ssh-pull-deploy.sh
```

---

### 情况 2：私钥已丢失（被随机 key 覆盖且未备份）

旧 PlatformAgent **无法恢复**，需要在 GitHub **换一对新 Deploy Key**：

1. GitHub → `Wwhqqqq/Economic_Agent_Platform` → **Settings** → **Deploy keys**  
2. **删除** 旧的 PlatformAgent（或 Edit 替换公钥）  
3. 在服务器（网页终端）**只生成一次**新密钥（仅在此情况下）：

```bash
ssh-keygen -t ed25519 -C "PlatformAgent-v2" -f ~/.ssh/platform_agent -N ""
chmod 600 ~/.ssh/platform_agent
cat ~/.ssh/platform_agent.pub
```

4. 把 `.pub` 内容添加到 GitHub Deploy keys，名称仍可用 `PlatformAgent`  
5. 配置 `~/.ssh/config`（同上）  
6. `ssh -T git@github.com` 测试通过后执行 `bash deploy/ssh-pull-deploy.sh`

---

## 清理服务器上误生成的密钥（可选）

```bash
# 查看当前 ~/.ssh
ls -la ~/.ssh/

# 删除误生成的（确认不是你要保留的）
# rm -f ~/.ssh/id_ed25519_github ~/.ssh/id_ed25519_github.pub
```

**不要**删除 `platform_agent`，除非确定要按情况 2 重建。

---

## 以后正确流程（不要再 ssh-keygen）

1. 私钥只装一次：`install-platform-agent-key.ps1` 或 `install-platform-agent-key.sh`  
2. 日常更新：`bash deploy/ssh-pull-deploy.sh`  
3. 本机触发：`.\deploy\ssh-pull-deploy.ps1`

脚本**只使用已有私钥**，永远不会自动生成或覆盖密钥。

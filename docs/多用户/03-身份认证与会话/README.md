# 03 — 身份认证与会话

## 1. 认证方案

沿用 **JWT Access Token** + 可选 Refresh Token + Redis 黑名单。与会员制结合时，Token 内需携带用户类型，避免每次查库（过期降级除外）。

### 1.1 JWT Payload

| 字段 | 说明 |
|------|------|
| `sub` | user_id（整数） |
| `username` | 展示名 |
| `user_type` | `regular` \| `member` |
| `membership_expires_at` | Unix 时间戳，普通用户可为 null |
| `exp` / `iat` / `jti` | 标准字段 |

**不在 JWT 中放**：密码、API Key、配额数字（配额走配置 + 实时查库）。

### 1.2 会员过期与 Token 一致性

登录或 Refresh 时服务端检查：

- 若 DB 中 `member` 已过期 → 更新为 `regular` 再签发 Token
- 短 TTL（1~2h）可自然刷新 user_type

## 2. 注册与登录

### 2.1 注册

```
POST /api/auth/register
{ username, email?, password }

→ INSERT users (user_type='regular', status='active')
→ 签发 JWT（user_type=regular）
→ audit: auth.register
```

开放注册默认**普通用户**；不提供注册时直接成为会员（防刷）。

### 2.2 登录

与通用流程相同，额外在签发 JWT 前执行**会员过期降级**检查。

### 2.3 会员状态查询

```
GET /api/membership/status
Authorization: Bearer

→ {
    user_type: "regular" | "member",
    membership_expires_at: "2026-12-31T00:00:00Z" | null,
    benefits: [ ... ]  // 可选，前端展示用
  }
```

### 2.4 支付 Webhook（会员开通）

```
POST /api/membership/webhook
Header: X-Payment-Signature
Body: { user_id | username, plan, expires_at, event }

1. 验证签名（HMAC 或支付平台公钥）
2. 幂等键防重复
3. UPDATE users SET user_type='member', membership_expires_at=?
4. audit: membership.activated
5. 不自动签发 Token；用户下次登录/Refresh 获得 member Token
```

## 3. REST 鉴权

```
get_current_user → UserContext
require_member() → user_type == 'member' else 403
check_membership_not_expired() → 内部降级或 403
```

**端点分类**：

| 类型 | 示例 |
|------|------|
| 公开 | login, register, health |
| 已登录 | sessions, 私有 knowledge |
| 仅会员 | mode=plan_execute（WS）, financial_audit execute |
| 资源级 | session 归属 |

移除原设计中的 `require_admin`、admin API。

## 4. WebSocket 鉴权

握手流程不变：Token → user_id → session 归属 → accept。

**新增：消息级门控**

```
收到 { mode: "collaborative_decision", ... }
if ctx.user_type != 'member':
    send error MEMBERSHIP_REQUIRED
    continue（不执行 Agent）
```

skill 字段同理：`financial_audit` 等会员技能拦截。

## 5. 会话生命周期

- 服务端 UUID，`POST /api/sessions`
- 创建前 `check_quota('session', user_id, user_type)`
- 普通用户达上限 → 429 + 提示升级会员

## 6. 前端改造

| 项 | 说明 |
|----|------|
| fetchMe / membership/status | 展示普通/会员标识 |
| ChatView 模式选择 | 会员专属项加锁，点击引导升级 |
| Skills 页 | 会员技能对普通用户显示「会员专享」 |
| 升级入口 | 跳转外链支付或兑换码弹窗 |

## 7. 匿名模式

`AUTH_ENABLED=false`：user_id=0，user_type=regular，便于本地开发。

## 8. 相关文档

- [04 — 权限与租户隔离](../04-权限与租户隔离/README.md)
- [07 — 存储与安全](../07-存储与安全/README.md)

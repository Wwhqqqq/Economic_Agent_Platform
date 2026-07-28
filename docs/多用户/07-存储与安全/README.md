# 07 — 存储与安全

## 1. 威胁模型

| 威胁 | 缓解 |
|------|------|
| 伪造身份 | JWT + HTTPS |
| 跨用户读会话/知识库 | user_id 归属 + filter |
| 普通用户蹭会员能力 | user_type 门控 + 过期降级 |
| 伪造支付 Webhook | 签名校验 + 幂等 |
| API Key 泄露 | 加密存储、仅会员可配（可选） |
| 登录爆破 | 限流 + 锁定 |
| 配额滥用 | 按 user_type 限流 |

移除「普通用户调 admin API」项；改为「伪造 Webhook 开通会员」「过期会员继续使用高级 mode」。

## 2. 密码安全

（bcrypt/Argon2、HTTPS、锁定策略，同前。）

## 3. JWT 与密钥

（JWT_SECRET、SETTINGS_ENCRYPTION_KEY、黑名单，同前。）

Token 中 `user_type` 为快照；**敏感操作**（可选）可强制查库校验会员未过期。

## 4. 用户 LLM API Key

**建议策略**：

- **普通用户**：仅使用平台 `.env` 提供的默认 Key，不可自配（防滥用与成本）
- **会员用户**：可在 Settings 配置个人 Key，AES-256-GCM 加密存库

若业务希望普通用户也可自配 Key，则两类用户均加密存储，但会员仍享高级模型权限。

## 5. 支付 Webhook 安全

| 项 | 要求 |
|----|------|
| HTTPS | 必须 |
| 签名 | HMAC-SHA256 或平台 RSA |
| 幂等 | external_order_id UNIQUE |
| IP 白名单 | 可选 |
| 日志 | audit membership.activated，不 log 完整卡号 |

## 6. MySQL / Chroma / Neo4j

（同前：内网访问、最小权限、参数化查询。）

会员专享库灌入通过**运维通道**，不暴露用户 API。

## 7. 文件上传

按 `user_type` 差异化大小限制；路径 `{user_id}/` 隔离。

## 8. 审计日志

**必须记录**：

- auth.login / fail / register
- membership.activated / expired / redeem
- knowledge.upload / delete（private）
- settings.change（会员 LLM）

用户仅可查 `actor_user_id = self`；**无全站审计 UI**。

## 9. code_executor

- 建议**仅会员**可用，或全员关闭
- 沙箱 + 超时

## 10. 安全检查清单

- [ ] AUTH_ENABLED=true
- [ ] JWT_SECRET / SETTINGS_ENCRYPTION_KEY 已更换
- [ ] Webhook 签名校验已启用
- [ ] 普通用户无法调用 member mode（自动化测试）
- [ ] 会员过期降级逻辑已测
- [ ] 越权用例全通过
- [ ] 无默认弱口令测试账号在生产

（移除「默认 admin 密码」项。）

## 11. 相关文档

- [03 — 身份认证与会话](../03-身份认证与会话/README.md)
- [04 — 权限与租户隔离](../04-权限与租户隔离/README.md)

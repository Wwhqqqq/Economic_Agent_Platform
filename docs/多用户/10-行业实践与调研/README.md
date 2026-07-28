# 10 — 行业实践与调研

## 1. 需求普遍性

「**免费普通用户 + 付费会员**」是 C 端 AI 产品最主流商业模式，与本设计完全一致：

| 产品 | 普通用户 | 会员 |
|------|----------|------|
| ChatGPT | Free，基础模型 | Plus，GPT-4、插件 |
| Claude | 免费额度 | Pro，更高限额 |
| Notion AI | 有限试用 | Plus 解锁 |
|  kimi / 文心 等 | 基础对话 | 会员模型与次数 |

本项目的 **regular / member** 对应 **Free / Plus** 两层，**不设 Admin 后台**的产品也常见（如早期 Notion 纯 self-serve + 运维）。

## 2. 为何不做管理员角色

| 考虑 | 说明 |
|------|------|
| 产品定位 | C 端 / 小团队 SaaS，非 B 端多租户运营平台 |
| 复杂度 | admin RBAC、审计 UI、用户管理大幅增 scope |
| 替代方案 | 运维脚本 + Webhook + DB 直接操作 |
| 会员制核心 | 差异化在 **member**，不在 **admin** |

若未来需要 B 端「企业版管理员」，应作为**独立产品线**而非与 C 端会员混在同一套 role 里。

## 3. 两级用户 vs 多角色 RBAC

| 模型 | 适用 |
|------|------|
| **两级 + 配额 + 功能门控（选定）** | Freemium AI 助手 |
| RBAC admin/user/guest | 企业内部系统 |
| ABAC | 复杂企业策略 |

调研结论：**ChatGPT 类产品的权限本质是 subscription tier，不是 RBAC role**。

## 4. 会员知识库行业做法

| 做法 | 示例 |
|------|------|
| 会员可读平台 curated 内容 | ChatGPT Plus 浏览、Custom GPT 商店 |
| 用户私有文档 | 全员均有，会员更高容量 |
| 会员专属模型/Agent | Plus 独享 GPT-4、o1 |

本项目：**private 用户自建 + member 平台灌库**，与「Plus 用户可访问增强知识/工具」一致。

## 5. 会员开通技术路径

| 方式 | 采用 |
|------|------|
| Stripe / 微信支付 Webhook | **推荐** Phase 4 |
| 兑换码 | 内测友好，Phase 3 可选 |
| 运维 SQL | 开发/赠送会员 |

无需应用内 admin 即可闭环。

## 6. MySQL + 向量库 + 会员 filter

与前一版调研一致：行级 user_id + metadata visibility；会员库用 `visibility=member` 而非全员 platform。

**注意**：原设计「platform 全员可见」改为 **「member 仅会员可见」**，更符合付费墙逻辑。

## 7. 常见反模式（更新）

| 反模式 | 后果 |
|--------|------|
| 仅前端隐藏会员按钮 | 后端 WS 仍可调 advanced mode |
| 会员状态只存前端 | 篡改 localStorage |
| member 库对 regular 可见 | 付费无价值 |
| 过期不降级 | 收入损失 |
| 引入 admin 又不做审计 | 半吊子后台 |

## 8. 调研结论

| 问题 | 结论 |
|------|------|
| 用户分几类？ | **仅 regular + member** |
| 谁管平台知识库？ | **运维灌库**，visibility=member |
| 谁开通会员？ | **Webhook / 兑换码 / 运维** |
| 高级 Agent？ | **member 专属** |
| MySQL？ | **仍然适用** |

## 9. 相关文档

- [01 — 需求与现状分析](../01-需求与现状分析/README.md)
- [04 — 权限与租户隔离](../04-权限与租户隔离/README.md)

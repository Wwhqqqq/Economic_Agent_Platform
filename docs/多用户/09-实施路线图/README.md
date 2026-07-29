# 09 — 实施路线图

## 1. 阶段总览

| 阶段 | 名称 | 交付价值 |
|------|------|----------|
| **Phase 0** | 基础设施 | MySQL、ORM、users 表含 user_type |
| **Phase 1** | 身份与会话 | 注册登录、WS 鉴权、会话隔离 |
| **Phase 2** | 记忆与 RAG 隔离 | user_id 全链路 + 私有知识库 |
| **Phase 3** | 会员体系 | 功能门控、会员库、Webhook、配额 |
| **Phase 4** | 安全与体验 | 加密、限流、前端升级 UX、支付对接 |

## 2. Phase 0

- docker-compose：mysql、redis
- users 表：`user_type`, `membership_expires_at`
- system_settings 配额种子数据
- Alembic 初始化

## 3. Phase 1 — 身份与会话 MVP

**后端**

- [ ] 注册（默认 regular）、登录、JWT 含 user_type
- [ ] get_current_user → UserContext
- [ ] sessions CRUD + MySQL 消息
- [ ] WS Token + 归属校验
- [ ] 移除/绕过 .env 单账号（生产）

**前端**

- [ ] WS token、后端创建 session
- [ ] 登录/注册页

**验收**：用户 A/B 会话隔离；无 Token 无法 WS。

## 4. Phase 2 — 记忆与 RAG 隔离

- [x] knowledge_documents（visibility=private）
- [x] Chroma / Neo4j user_id filter
- [x] MemoryManager 全链路 user_id
- [x] file_reader 用户目录
- [x] skill connection 级激活

**验收**：06 文档越权用例 1~4、7 通过。

## 5. Phase 3 — 会员体系

**后端**

- [ ] require_member() 门控：Plan-Execute、Multi-Agent、高阶 skill
- [ ] adaptive 路由：regular 仅 ReAct
- [ ] 会员专享库：运维灌库脚本 + visibility=member
- [ ] retrieve 按 user_type 分支
- [ ] GET /api/membership/status
- [ ] POST /api/membership/webhook（签名校验）
- [ ] 会员过期自动降级
- [ ] 配额 check：session 数、文档数
- [ ] user_llm_settings（会员可写）

**前端**

- [ ] 会员徽章、模式/技能加锁 UI
- [ ] 升级会员入口（占位或外链）
- [ ] 403 MEMBERSHIP_REQUIRED 提示

**数据**

- [ ] 灌入样例 member 知识库（会计学制度等）

**验收**：06 文档用例 3~6；普通用户调 multi_agent 返回 403。

## 6. Phase 4 — 安全与体验

- [ ] API Key 加密（会员）
- [ ] audit_logs 入库
- [ ] Redis 限流（分 user_type）
- [ ] 兑换码（可选）
- [ ] 真实支付对接
- [ ] Refresh Token、改密
- [ ] 负载测试

## 7. 团队分工

| 角色 | Phase 1~2 | Phase 3 |
|------|-----------|---------|
| 后端 A | auth + sessions | membership gate + webhook |
| 后端 B | RAG + memory | 会员库灌库 + 配额 |
| 前端 | auth + WS | 会员 UI |
| 运维 | MySQL | 灌库脚本 + Webhook 密钥 |

## 8. 风险

| 风险 | 缓解 |
|------|------|
| 会员门控遗漏 | 集中 FeatureGate + 集成测试矩阵 |
| Webhook 伪造 | 签名校验 |
| 过期仍能用 | 登录/Refresh 强制降级 |
| scope 膨胀 | 不做管理端 |

## 9. 里程碑

| 里程碑 | 标志 |
|--------|------|
| M1 | Phase 1，多用户隔离 |
| M2 | Phase 2，RAG 私有 |
| M3 | Phase 3，会员闭环可演示 |
| M4 | Phase 4，可公测 |

## 10. 相关文档

- [01 — 需求](../01-需求与现状分析/README.md)
- [Phase 2 开发手册（记忆与 RAG 隔离）](./phase2/README.md)
- [04 — 权限](../04-权限与租户隔离/README.md)

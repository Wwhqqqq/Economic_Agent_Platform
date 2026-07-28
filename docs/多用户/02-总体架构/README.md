# 02 — 总体架构

## 1. 架构演进

### 1.1 现状（单租户）

```
Frontend ──REST/WS──► FastAPI
                         ├── 内存 ShortTermMemory
                         ├── Chroma / Neo4j（无 tenant）
                         ├── settings.json（全局）
                         └── 可选单账号 JWT
```

### 1.2 目标（多用户 + 普通/会员）

```
Frontend ──REST/WS(+JWT)──► FastAPI
                                ├── Auth + Membership Gate（user_id, user_type）
                                ├── MySQL（用户、会员、会话、消息、配额）
                                ├── Redis（Token 黑名单、限流、可选缓存）
                                ├── Chroma（user_id + visibility filter）
                                └── Neo4j（user_id + visibility filter）
```

## 2. 核心组件

### 2.1 Identity Service

- 注册（默认 `user_type=regular`）、登录、改密
- JWT 含 `user_id`、`user_type`、`membership_expires_at`
- 会员过期自动降级

### 2.2 Membership Service

- 查询会员状态
- 支付 Webhook 开通 / 续费
- 兑换码（可选）
- **不提供**应用内管理 UI

### 2.3 Session / Message Service

- 服务端 UUID，绑定 user_id
- WS 鉴权 + 归属校验

### 2.4 Feature Gate（功能门控）

- 根据 `user_type` 拦截 execution_mode、skill、RAG 范围
- 根据配额拦截 session 创建、上传

### 2.5 Tenant Context

```
RequestContext:
  user_id: int
  username: str
  user_type: regular | member
  membership_expires_at: datetime | None
  session_id: str | None
```

### 2.6 Knowledge Service

- 私有库：用户上传，visibility=private
- 会员库：运维灌库，visibility=member，**仅 member 检索**

### 2.7 Settings Service

- 平台默认 LLM：`.env`（全员 fallback）
- 个人 LLM 配置：`user_llm_settings`，**建议仅会员可配置**

## 3. 请求链路（含会员门控）

```
1. 注册/登录 → JWT（user_type=regular|member）

2. POST /api/sessions → 检查会话配额 → 创建 session

3. WS 连接 ?token= → 校验 Token + session 归属

4. WS message { mode, skill, input }
   → 若 mode/skill 需会员且 user_type=regular → error
   → MemoryManager.load（RAG 按 user_type 决定是否含 member 库）
   → AgentOrchestrator.stream
   → save_context

5. GET /api/membership/status → 前端展示会员徽章 / 升级入口
```

## 4. 平台运维入口（非应用 UI）

| 操作 | 方式 |
|------|------|
| 灌入会员专享知识库 | 脚本 / CLI 写 Chroma+Neo4j，visibility=member |
| 调整系统配额 | `.env` 或 `system_settings` 表，运维改库 |
| 禁用用户 | 运维 UPDATE users.status |
| 手动开通会员 | 运维 UPDATE user_type + expires_at |
| 支付自动开通 | Webhook → Membership Service |

## 5. 部署拓扑

与原先一致：Nginx + FastAPI × N + MySQL + Redis + Chroma + Neo4j。FastAPI **无状态**，skill 激活用 connection 级上下文。

## 6. 模块改造映射

| 现有模块 | 改造 |
|----------|------|
| `orchestrator._select_mode` | 高级模式前 require member |
| `auth.py` | user_type + 过期降级 |
| `hybrid.retrieve` | 按 user_type 构造 visibility filter |
| `settings_store` | 会员个人配置进 MySQL |
| 前端 ChatView | 灰显会员专属 mode/skill |

## 7. 失败 closed

- Token 无效 → 401
- 非会员调会员功能 → 403 MEMBERSHIP_REQUIRED
- 配额用尽 → 429
- session 不归属 → 403

## 8. 相关文档

- [04 — 权限与租户隔离](../04-权限与租户隔离/README.md)
- [05 — 数据模型](../05-数据模型与MySQL设计/README.md)

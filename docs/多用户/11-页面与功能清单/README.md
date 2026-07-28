# 11 — 页面变更清单与功能总表

本文档基于 [多用户体系设计](../README.md)（普通用户 / 会员用户、MySQL、全链路隔离）整理，供产品评审与开发排期使用。列出的后端能力为**需要新增或改造**的项，不含已满足且无需改动的只读展示逻辑。

---

## 一、页面与路由变更清单

### 1.1 新增页面

| 页面 | 路由 | 优先级 | 说明 |
|------|------|--------|------|
| **注册页** | `/register` | P0 | 用户名、邮箱（可选）、密码、确认密码；注册成功跳转登录或自动登录 |
| **会员中心** | `/membership` | P1 | 展示当前身份（普通/会员）、到期时间、权益对比、升级入口 |
| **兑换码页** | `/membership/redeem` | P2 | 输入兑换码开通/延长会员；可合并进会员中心 |
| **账号安全** | `/account/security` | P2 | 修改密码；可合并进设置页 Tab |
| **我的操作记录** | `/account/activity` | P3 | 当前用户审计日志（登录、上传、改设置等） |

### 1.2 需修改的现有页面

| 页面 | 路由 | 优先级 | 修改要点 |
|------|------|--------|----------|
| **登录页** | `/login` | P0 | 增加「去注册」链接；去掉或隐藏默认 admin 预填；登录失败提示；支持登录后拉取 `user_type` |
| **应用壳** | `App.vue` | P0 | 侧栏展示用户昵称 + 会员徽章；**登出按钮**；会话列表仅当前用户；401 全局处理 |
| **聊天页** | `/` | P0 | WS 携带 Token；**新建对话改调 POST /api/sessions**；执行模式/技能对普通用户**加锁**；403 会员提示；展示配额（会话数等） |
| **技能页** | `/skills` | P1 | 技能卡片标注「会员专享」；试用执行拦截会员技能；展示 `membership_required` 引导 |
| **Agent 页** | `/agents` | P1 | 任务编排、协同决策等引擎卡片标注会员专属；只读说明升级权益 |
| **知识库页** | `/knowledge` | P1 | 文档列表分「我的文档 / 会员专享」（会员可见后者）；上传前配额提示；删除仅限自己的 private |
| **设置页** | `/settings` | P1 | **普通用户**：只读平台默认 LLM 或简化项；**会员**：完整 API Key、模型配置；增加跳转会员中心 |
| **工具页** | `/tools` | P2 | 可选：标注 `code_executor` 等会员专属工具（说明性，只读） |

### 1.3 无需新增但需改动的非页面模块

| 模块 | 文件（参考） | 优先级 | 修改要点 |
|------|--------------|--------|----------|
| 路由守卫 | `router/index.ts` | P0 | 未登录跳转；注册路由公开；可选：会员页需登录 |
| 认证 Store | `stores/auth.ts` | P0 | 存 `user_id`、`user_type`、`membership_expires_at`；register/logout/refresh |
| 聊天 Store | `stores/chat.ts` | P0 | WS URL 带 token；createSession API；处理 `MEMBERSHIP_REQUIRED` 错误 |
| WebSocket | `api/websocket.ts` | P0 | 连接参数 token；断线重连（P2） |
| API 客户端 | `api/client.ts` | P0 | 新增 auth/membership/sessions 接口；401 拦截 |
| 设置 Store | `stores/settings.ts` | P1 | 与会员态联动；模式选择过滤 |
| 会员 Store（新） | `stores/membership.ts` | P1 | 会员状态、权益列表、配额余量 |
| 展示文案 | `utils/displayLabels.ts` | P1 | 会员标签、错误码文案 |
| 全局样式 | 可选组件 | P2 | `MembershipBadge.vue`、`UpgradePrompt.vue`、`LockedFeature.vue` |

### 1.4 页面结构示意（改后）

```
/login                    登录
/register                 注册（新）
/                         聊天（改）
/tools                    工具（小改）
/skills                   技能（改）
/agents                   Agent 档案（改）
/knowledge                知识库（改）
/settings                 设置（改）
/membership               会员中心（新）
/membership/redeem        兑换码（新，可合并）
/account/security         改密（新，可合并到 settings）
/account/activity         我的记录（新，P3）
```

---

## 二、功能总表 — 后端

### 2.1 基础设施与数据层

| ID | 功能 | 类型 | 优先级 | Phase | 说明 |
|----|------|------|--------|-------|------|
| B-01 | MySQL 接入 | 新增 | P0 | 0 | docker-compose、DATABASE_URL、连接池 |
| B-02 | Redis 接入 | 新增 | P1 | 3 | 黑名单、限流、可选缓存 |
| B-03 | Alembic 迁移 | 新增 | P0 | 0 | schema 版本管理 |
| B-04 | users 表 | 新增 | P0 | 0 | 含 user_type、membership_expires_at |
| B-05 | chat_sessions 表 | 新增 | P0 | 1 | 服务端 UUID，绑定 user_id |
| B-06 | chat_messages 表 | 新增 | P0 | 1 | 消息持久化 |
| B-07 | knowledge_documents 表 | 新增 | P1 | 2 | visibility: private / member |
| B-08 | user_llm_settings 表 | 新增 | P1 | 3 | 会员个人 LLM 配置 |
| B-09 | system_settings 表 | 新增 | P1 | 3 | 配额与功能开关（运维维护） |
| B-10 | audit_logs 表 | 新增 | P2 | 4 | 替代/补充文件 audit.log |
| B-11 | membership_orders 表 | 新增 | P2 | 4 | 支付流水（可选） |
| B-12 | membership_codes 表 | 新增 | P2 | 3 | 兑换码（可选） |
| B-13 | refresh_tokens 表 | 新增 | P2 | 4 | Refresh Token（可选） |

### 2.2 身份认证

| ID | 功能 | 类型 | 优先级 | Phase | 说明 |
|----|------|------|--------|-------|------|
| A-01 | 用户注册 | 新增 | P0 | 1 | POST /api/auth/register，默认 regular |
| A-02 | 用户登录 | 修改 | P0 | 1 | MySQL 校验密码；JWT 含 user_id、user_type |
| A-03 | 获取当前用户 | 修改 | P0 | 1 | GET /api/auth/me 返回完整 UserContext |
| A-04 | 用户登出 | 新增 | P1 | 3 | POST /api/auth/logout，jti 黑名单 |
| A-05 | 修改密码 | 新增 | P2 | 4 | POST /api/auth/change-password |
| A-06 | Refresh Token | 新增 | P2 | 4 | 换发 Access Token（可选） |
| A-07 | 密码 bcrypt 存储 | 新增 | P0 | 1 | 替代 .env 明文比对 |
| A-08 | 登录失败锁定 | 新增 | P1 | 3 | login_attempts / locked_until |
| A-09 | 会员过期自动降级 | 新增 | P1 | 3 | 登录/Refresh 时 regular 化 |
| A-10 | JWT 黑名单 | 新增 | P1 | 3 | Redis 存 jti |

### 2.3 会员体系

| ID | 功能 | 类型 | 优先级 | Phase | 说明 |
|----|------|------|--------|-------|------|
| M-01 | 会员状态查询 | 新增 | P1 | 3 | GET /api/membership/status |
| M-02 | 支付 Webhook 开通 | 新增 | P1 | 3 | POST /api/membership/webhook，签名校验 |
| M-03 | 兑换码兑换 | 新增 | P2 | 3 | POST /api/membership/redeem |
| M-04 | 权益/配额查询 | 新增 | P1 | 3 | GET /api/membership/quota（会话数、文档数余量） |
| M-05 | 功能门控 require_member | 新增 | P1 | 3 | 装饰器/依赖，403 MEMBERSHIP_REQUIRED |
| M-06 | 会员专享知识库灌库脚本 | 新增 | P1 | 3 | 运维 CLI，visibility=member |
| M-07 | 配额校验 | 新增 | P1 | 3 | 创建 session、上传文档前检查 |

### 2.4 会话与聊天

| ID | 功能 | 类型 | 优先级 | Phase | 说明 |
|----|------|------|--------|-------|------|
| C-01 | 创建会话 | 新增 | P0 | 1 | POST /api/sessions，服务端 UUID |
| C-02 | 会话列表 | 修改 | P0 | 1 | 仅当前 user_id |
| C-03 | 会话重命名 | 修改 | P0 | 1 | 归属校验 |
| C-04 | 删除/清空会话 | 修改 | P0 | 1 | 归属校验 + 清 MySQL/Chroma/Neo4j |
| C-05 | 获取历史消息 | 修改 | P0 | 1 | 归属校验，从 MySQL 读 |
| C-06 | WebSocket 鉴权 | 修改 | P0 | 1 | 握手校验 JWT + session 归属 |
| C-07 | WS 会员模式门控 | 新增 | P1 | 3 | plan_execute、multi_agent 等拦截 |
| C-08 | WS 会员技能门控 | 新增 | P1 | 3 | financial_audit 等拦截 |
| C-09 | skill 连接级上下文 | 修改 | P1 | 2 | 取消全局 skill_registry 污染 |
| C-10 | AgentConfig.user_id | 修改 | P0 | 1 | 贯穿编排与记忆 |

### 2.5 记忆系统

| ID | 功能 | 类型 | 优先级 | Phase | 说明 |
|----|------|------|--------|-------|------|
| R-01 | 短期记忆持久化 | 修改 | P0 | 1 | 内存 dict → MySQL |
| R-02 | 长期记忆 user_id | 修改 | P1 | 2 | Chroma metadata + filter |
| R-03 | 情景记忆 user_id | 修改 | P1 | 2 | Neo4j 节点 + Cypher filter |
| R-04 | MemoryManager 传 user_type | 修改 | P1 | 3 | RAG 是否含 member 库 |
| R-05 | 会员长期记忆开关 | 新增 | P2 | 3 | 普通用户可关闭长期记忆 |

### 2.6 知识库与 RAG

| ID | 功能 | 类型 | 优先级 | Phase | 说明 |
|----|------|------|--------|-------|------|
| K-01 | 上传写入 user_id | 修改 | P1 | 2 | private 文档 |
| K-02 | 文档列表按用户过滤 | 修改 | P1 | 2 | private +（会员）member 只读列表 |
| K-03 | 删除归属校验 | 修改 | P1 | 2 | 仅 owner 删 private |
| K-04 | 检索 tenant filter | 修改 | P1 | 2 | 向量 + 图谱双路 filter |
| K-05 | 会员专享库检索 | 新增 | P1 | 3 | 仅 member 的 visibility=member |
| K-06 | 上传递配额校验 | 新增 | P1 | 3 | 按 user_type 限制 |
| K-07 | file_reader 用户目录 | 修改 | P1 | 2 | uploads/{user_id}/ |

### 2.7 Agent 编排与技能

| ID | 功能 | 类型 | 优先级 | Phase | 说明 |
|----|------|------|--------|-------|------|
| G-01 | adaptive 路由限制 | 修改 | P1 | 3 | regular 仅路由 ReAct |
| G-02 | Plan-Execute 会员门控 | 新增 | P1 | 3 | orchestrator / WS |
| G-03 | Multi-Agent 会员门控 | 新增 | P1 | 3 | 同上 |
| G-04 | 技能列表返回 membership_required | 修改 | P1 | 3 | API 元数据供前端加锁 |
| G-05 | 技能 execute 会员门控 | 修改 | P1 | 3 | POST /api/skills/{name}/execute |
| G-06 | code_executor 会员门控 | 新增 | P2 | 3 | 工具层或策略配置 |

### 2.8 设置与 LLM

| ID | 功能 | 类型 | 优先级 | Phase | 说明 |
|----|------|------|--------|-------|------|
| S-01 | 个人 LLM 配置入库 | 修改 | P1 | 3 | 替代全局 settings.json 用户部分 |
| S-02 | API Key 加密存储 | 新增 | P1 | 4 | AES-256-GCM |
| S-03 | 普通用户只读平台默认 | 修改 | P1 | 3 | GET settings 按 user_type 分支 |
| S-04 | 会员写入个人 LLM | 修改 | P1 | 3 | PUT 仅 member |
| S-05 | 平台 settings 运维只读 | 修改 | P1 | 3 | 应用内不可写 system_settings |

### 2.9 安全、审计与运维

| ID | 功能 | 类型 | 优先级 | Phase | 说明 |
|----|------|------|--------|-------|------|
| X-01 | 全 REST 鉴权 | 修改 | P0 | 1 | Depends get_current_user |
| X-02 | 登录/注册限流 | 新增 | P1 | 3 | Redis 按 IP |
| X-03 | API 按用户限流 | 新增 | P2 | 4 | 分 user_type |
| X-04 | 审计日志写 MySQL | 新增 | P2 | 4 | 登录、上传、会员开通等 |
| X-05 | GET 我的审计记录 | 新增 | P3 | 4 | GET /api/account/activity |
| X-06 | /health 含 MySQL | 修改 | P0 | 0 | 健康检查扩展 |
| X-07 | 数据迁移脚本 | 新增 | P1 | 2 | 旧数据/匿名桶/会员样例库 |
| X-08 | 种子用户脚本 | 新增 | P1 | 1 | 测试 regular + member 账号 |

---

## 三、功能总表 — 前端

| ID | 功能 | 类型 | 优先级 | Phase | 关联页面/模块 |
|----|------|------|--------|-------|---------------|
| F-01 | 注册表单与流程 | 新增 | P0 | 1 | RegisterView |
| F-02 | 登录拉取 user_type | 修改 | P0 | 1 | LoginView, auth store |
| F-03 | 侧栏登出 | 新增 | P0 | 1 | App.vue |
| F-04 | 会员徽章展示 | 新增 | P1 | 3 | App.vue, MembershipBadge |
| F-05 | WS 连接携带 Token | 修改 | P0 | 1 | websocket.ts |
| F-06 | 后端创建会话 | 修改 | P0 | 1 | chat store, ChatView |
| F-07 | 执行模式会员加锁 | 新增 | P1 | 3 | ChatView, settings store |
| F-08 | 技能选择会员加锁 | 新增 | P1 | 3 | ChatView, SkillsView |
| F-09 | MEMBERSHIP_REQUIRED 提示 | 新增 | P1 | 3 | ChatView 全局 |
| F-10 | 升级会员引导弹窗 | 新增 | P1 | 3 | UpgradePrompt 组件 |
| F-11 | 会员中心页 | 新增 | P1 | 3 | MembershipView |
| F-12 | 权益对比表 | 新增 | P1 | 3 | MembershipView |
| F-13 | 升级外链/占位按钮 | 新增 | P2 | 4 | MembershipView |
| F-14 | 兑换码输入 | 新增 | P2 | 3 | RedeemView |
| F-15 | 配额余量展示 | 新增 | P1 | 3 | ChatView, KnowledgeView |
| F-16 | 知识库分区列表 | 修改 | P1 | 3 | KnowledgeView |
| F-17 | 设置页按会员分支 | 修改 | P1 | 3 | SettingsView |
| F-18 | Agent 页会员标注 | 修改 | P1 | 3 | AgentsView |
| F-19 | 401 统一跳登录 | 修改 | P0 | 1 | client.ts interceptor |
| F-20 | 改密表单 | 新增 | P2 | 4 | AccountSecurity |
| F-21 | 我的操作记录 | 新增 | P3 | 4 | AccountActivity |
| F-22 | 注册/登录路由守卫 | 修改 | P0 | 1 | router |
| F-23 | fetchMembershipStatus | 新增 | P1 | 3 | membership store, client.ts |
| F-24 | fetchQuota | 新增 | P1 | 3 | membership store |

---

## 四、功能总表 — 基础设施与运维（无 UI）

| ID | 功能 | 优先级 | Phase | 说明 |
|----|------|--------|-------|------|
| O-01 | docker-compose 增加 MySQL | P0 | 0 | |
| O-02 | docker-compose 增加 Redis | P1 | 3 | |
| O-03 | .env 新增 DATABASE_URL 等 | P0 | 0 | |
| O-04 | 会员知识库灌库 CLI | P1 | 3 | 会计学等样例文档 |
| O-05 | 手动开通会员 SQL/脚本 | P1 | 3 | 内测赠送 |
| O-06 | 支付平台 Webhook 密钥配置 | P1 | 3 | 环境变量 |
| O-07 | HTTPS / WSS 部署说明 | P1 | 4 | 生产必项 |
| O-08 | MySQL 备份策略 | P2 | 4 | |

---

## 五、按 Phase 交付汇总

| Phase | 页面 | 功能 ID 范围（概要） |
|-------|------|---------------------|
| **0** | 无 | B-01~04, B-13, O-01~03, X-06 |
| **1** | 改 Login、App、Chat；增 Register | A-01~03,07；C-01~06,10；R-01；F-01~03,05~06,19,22；X-01,08 |
| **2** | 小改 Knowledge | B-07；K-01~04,07；R-02~03；C-09；X-07 |
| **3** | 改 Chat、Skills、Agents、Knowledge、Settings；增 Membership | M-01~07；G-01~05；K-05~06；S-01,03~05；R-04；C-07~08；F-04,07~18,23~24；O-04~06 |
| **4** | 增 Redeem、改密、Activity；完善 Membership | A-04~06；B-08~12；S-02；X-02~05；F-13~14,20~21；O-07~08 |

---

## 六、统计

| 类别 | 新增 | 修改 | 合计 |
|------|------|------|------|
| 页面（含可合并子页） | 5 | 8 | 13 |
| 前端模块/Store/组件 | 12+ | 10+ | 22+ |
| 后端功能项 | 55+ | 25+ | **80+** |
| 运维项 | 8 | — | 8 |

---

## 七、相关文档

- [01 — 需求与现状分析](../01-需求与现状分析/README.md)
- [04 — 权限与租户隔离](../04-权限与租户隔离/README.md)
- [09 — 实施路线图](../09-实施路线图/README.md)
- [API 与前端（现有）](../../api-frontend/README.md)

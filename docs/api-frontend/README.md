# API 与前端模块

## 模块职责

API 层（FastAPI）与前端（Vue 3）共同构成用户与后端智能体能力的**交互界面**。后端模块负责「怎么算」，本模块负责「怎么触达、怎么展示」。

## 后端 API 架构

### 路由组织

`main.py` 挂载 10 组路由器：

| 前缀 | 模块文件 | 职责 |
|------|----------|------|
| `/ws/chat/{session_id}` | `api/chat.py` | WebSocket 实时对话 |
| `/api/sessions` | `api/chat.py` | 会话列表、消息、重命名、删除 |
| `/api/tools` | `api/tools.py` | 工具目录 |
| `/api/skills` | `api/skills.py` | 技能目录、激活、执行 |
| `/api/agents` | `api/agents.py` | Agent 档案与 execution_modes |
| `/api/knowledge` | `api/knowledge.py` | 知识库 CRUD 与检索 |
| `/api/settings/llm` | `api/settings.py` | LLM 配置 |
| `/api/catalog` | `api/catalog.py` | 平台元数据与标签 |
| `/api/auth` | `api/auth.py` | 登录与当前用户 |
| `/api/system/status` | `api/system.py` | 系统状态 |
| `/api/audit/logs` | `api/audit.py` | 审计日志（admin） |

另：`GET /health` 健康检查、`GET /api/docs` Swagger UI。

### WebSocket 聊天协议（核心）

**连接**：`ws://host/ws/chat/{session_id}`

**客户端发送**（JSON）：

```json
{
  "type": "message",
  "input": "用户问题",
  "mode": "adaptive",
  "skill": "financial_audit",
  "provider": "deepseek",
  "model": "deepseek-v4-pro",
  "temperature": 0.7
}
```

**服务端推送**（JSON）：

```json
{
  "type": "reasoning",
  "data": { "content": "...", "accumulated": true }
}
```

主要 `type` 值：`start`、`thinking`、`tool_call`、`tool_result`、`reasoning`、`citation`、`step`、`intermediate`、`final`、`done`、`error`

**超时**：单次处理受 `AGENT_TIMEOUT_SECONDS`（默认 120s）约束。

**流程**：
1. 解析消息，可选 `skill_registry.activate(skill)`
2. 构造 `AgentConfig(session_id=...)`
3. `AgentOrchestrator.stream()` 异步迭代事件
4. 每条事件 JSON 序列化后 send
5. 异常时发送 `error` 事件

### 认证（可选）

- `AUTH_ENABLED=false` 时默认关闭，所有 API 匿名可访问
- 开启后：JWT Bearer Token，`POST /api/auth/login` 获取 token
- 保护路由：知识库上传/删除、LLM 设置、审计日志
- WebSocket **当前未携带 Token**，依赖 session_id（生产需加固）

### 审计日志

`audit_log.py` 以 JSON Lines 写入 `data/audit.log`，记录 login、upload、settings 变更等。API 已暴露但**前端暂无页面**。

## 前端架构

### 技术栈

Vue 3 Composition API · TypeScript · Pinia · Vue Router · Element Plus · Axios · Vite · markdown-it

### 应用壳（App.vue）

持久布局：左侧边栏 + 右侧 `router-view`。

**侧边栏**：
- 平台名称（来自 catalog）
- 健康状态 pill（/health）
- 会话列表 + 新建对话
- 导航：聊天、工具、技能、Agent、知识库、设置

**挂载时初始化**：`platformStore.load()`、`systemStore.refresh()`、`chatStore.connect()`、`chatStore.loadSessions()`

### 路由与鉴权

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | LoginView | 用户名密码登录 |
| `/` | ChatView | 默认聊天工作台 |
| `/tools` | ToolsView | 工具浏览 |
| `/skills` | SkillsView | 技能管理与试运行 |
| `/agents` | AgentsView | Agent 档案只读 |
| `/knowledge` | KnowledgeView | 知识库管理 |
| `/settings` | SettingsView | LLM 与基础设施 |

路由守卫：auth 启用且无 token → 跳转 `/login`；已登录访问 `/login` → 跳 `/`

### Pinia 状态管理

| Store | 职责 |
|-------|------|
| `auth` | token、username、login/logout、localStorage 持久化 |
| `chat` | 消息列表、WebSocket、会话 CRUD、流式事件处理 |
| `platform` | 平台名、executionModes（catalog） |
| `system` | /health 聚合状态 |
| `settings` | 当前选的 mode/skill/provider/model（UI 态，非持久） |

**chatStore 事件处理摘要**：

- `reasoning` → 追加/更新 assistant 消息 content（流式 Markdown）
- `tool_call` / `tool_result` → 工具卡片
- `citation` → 引用来源列表
- `step` / `intermediate` → 时间线步骤
- `final` → 定稿 + token 统计
- `done` → 结束 loading，刷新会话列表

### API 客户端（api/client.ts）

- Axios `baseURL: '/api'`，timeout 120s
- 请求拦截器自动附加 `Authorization: Bearer`
- `fetchSystemStatus()` 单独请求 `/health`（不在 /api 下）

### WebSocket 客户端（api/websocket.ts）

- URL：`ws(s)://{host}/ws/chat/{sessionId}`
- 开发环境经 Vite 代理 `/ws → ws://localhost:8000`
- 10s 连接超时；`connectPromise` 防重复连接
- 监听器模式：`on(type, handler)` 供 chatStore 订阅

### Vite 开发代理

```
/api    → http://localhost:8000
/health → http://localhost:8000
/ws     → ws://localhost:8000
```

前端 dev 端口：**3000**（`127.0.0.1:3000`）

## 页面与后端模块映射

| 用户操作 | 前端 | 后端模块 |
|----------|------|----------|
| 发送聊天消息 | ChatView + chatStore WS | Agent 编排 + 记忆 + 技能 |
| 切换执行模式 | settingsStore.mode → WS | AgentOrchestrator 路由 |
| 激活技能 | REST activate + WS skill 字段 | SkillRegistry |
| 浏览工具 | ToolsView GET /tools | ToolRegistry |
| 试运行技能 | SkillsView POST execute | SkillExecutor |
| 查看 Agent 档案 | AgentsView GET /agents | catalog + AGENT_PROFILES |
| 上传/检索知识 | KnowledgeView /knowledge/* | RAG HybridRetriever |
| 配置 API Key | SettingsView PUT /settings/llm | LLMFactory + settings_store |
| 查看系统健康 | App pill + Settings tags | health service |

## UI 组件与设计

- **玻璃态风格**：GlassCard、DecorativeBg、theme.css 中 indigo/cyan 渐变
- **displayLabels.ts**：工具/技能/步骤的中文产品化名称，与 catalog API 合并
- **设计系统**：`design-system/agentworkbench/MASTER.md` 为设计规范；实现色板以 `theme.css` 为准

## 已知前端限制

1. WebSocket 无自动重连
2. 侧边栏无 logout 按钮（auth store 有 logout 方法）
3. `fetchAuditLogs` 无对应页面
4. markdown-it 渲染未做 XSS  sanitization（仅受信内容）
5. Chat 与 Settings 的 provider 同步依赖 WS 是否传 override
6. `/login` 仍在带侧边栏的 App 壳内，非独立 auth layout

## 代码位置

**后端 API**：`backend/app/api/*.py`

**前端**：
- `frontend/src/views/` — 页面
- `frontend/src/stores/` — Pinia
- `frontend/src/api/` — HTTP + WS
- `frontend/src/router/index.ts` — 路由

## 相关文档

- [系统总览](../system-overview/README.md) — 端到端请求链路
- [Agent 编排](../agent-orchestration/README.md) — WS 背后的执行逻辑
- 既有答辩文档：`docs/defense/08-API与前端交互.md`（部分已过时，以本文为准）

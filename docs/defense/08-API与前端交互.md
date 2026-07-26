# 08 — API 与前端交互

本模块讲解前后端通信协议、WebSocket 事件流和 Vue 工作台 UI 架构。

---

## 1. API 总览

| 类型 | 端点 | 说明 |
|------|------|------|
| WebSocket | `WS /ws/chat/{session_id}` | 实时聊天（核心） |
| REST | `GET /api/tools` | 工具列表 |
| REST | `GET /api/skills` | 技能列表 |
| REST | `POST /api/skills/{name}/activate` | 激活技能 |
| REST | `GET /api/agents` | Agent 档案 |
| REST | `GET /api/agents/models` | 可用 LLM 模型 |
| REST | `POST /api/knowledge/upload` | 上传知识文档 |
| REST | `POST /api/knowledge/search` | 知识检索 |
| REST | `GET/PUT /api/settings/llm` | LLM 配置 |
| REST | `GET /api/catalog` | 平台元数据 |
| REST | `DELETE /api/sessions/{id}` | 清除会话记忆 |
| REST | `GET /health` | 健康检查 |

**API 文档：** `http://localhost:8000/api/docs`（Swagger UI）

---

## 2. WebSocket 聊天协议

**文件：** `backend/app/api/chat.py`

### 2.1 连接

```
ws://localhost:8000/ws/chat/{session_id}
```

连接成功后服务端推送：

```json
{ "type": "connected", "data": { "session_id": "session_xxx" } }
```

### 2.2 客户端 → 服务端

```json
{
  "type": "message",
  "input": "用户的输入文本",
  "mode": "adaptive",
  "skill": "financial_audit",
  "provider": "deepseek",
  "model": null,
  "temperature": 0.7
}
```

| 字段 | 说明 | 可选值 |
|------|------|--------|
| `input` | 用户消息 | 必填 |
| `mode` | 执行模式 | adaptive / reasoning_action / task_orchestration / collaborative_decision |
| `skill` | 激活技能 | financial_audit / document_analysis / data_visualization / null |
| `temperature` | LLM 温度 | 0.0 – 1.0 |

**注意：** `provider` 字段前端会发送，但后端 Agent 运行时固定使用 DeepSeek。

### 2.3 服务端 → 客户端（事件流）

| 事件 type | 含义 | data 关键字段 |
|-----------|------|--------------|
| `connected` | 连接成功 | session_id |
| `start` | 任务开始 | execution_mode, active_skill, provider |
| `thinking` | 正在思考 | iteration, message, role, phase |
| `tool_call` | 发起工具调用 | tool, args |
| `tool_result` | 工具返回 | tool, result |
| `reasoning` | 推理文本流 | token, accumulated |
| `intermediate` | 中间步骤 | phase, steps, overview, round |
| `final` | 最终输出 | output, tool_calls |
| `error` | 错误 | message |
| `done` | 执行结束 | — |

### 2.4 典型事件序列

**ReAct 模式：**
```
connected → start → thinking → [tool_call → tool_result]* → reasoning* → final → done
```

**Plan-Execute 模式：**
```
connected → start → thinking(planning)
  → intermediate(phase=plan)
  → intermediate(phase=execute_start) → thinking → tool_call → tool_result → intermediate(phase=execute_done)
  → intermediate(phase=evaluate)
  → thinking(aggregate) → reasoning → final → done
```

**辩论模式：**
```
connected → start
  → intermediate(debate_round, round=1)
  → thinking(role=analyst) → tool_call → tool_result → reasoning
  → thinking(role=skeptic) → tool_call → tool_result → reasoning
  → thinking(role=judge) → reasoning
  → [重复 round 2, 3]
  → final(mode=debate_verdict) → done
```

---

## 3. 后端处理流程

```python
# chat.py 核心逻辑
async def websocket_chat(websocket, session_id):
    await websocket.accept()
    await websocket.send_json({"type": "connected", ...})

    while True:
        data = json.loads(await websocket.receive_text())

        # 1. 技能激活
        if data.get("skill"):
            skill_registry.activate(data["skill"])
        else:
            skill_registry.deactivate()

        # 2. 构建配置
        agent_config = AgentConfig(
            session_id=session_id,
            temperature=data.get("temperature", 0.7),
        )

        # 3. 流式执行
        mode = normalize_execution_mode(data.get("mode", "adaptive"))
        async for event in orchestrator.stream(input, agent_config, mode):
            await websocket.send_json({
                "type": event.type.value,
                "data": event.data,
                "metadata": event.metadata,
            })
```

---

## 4. 前端架构

### 4.1 技术栈

| 技术 | 用途 |
|------|------|
| Vue 3 + Composition API | UI 框架 |
| TypeScript | 类型安全 |
| Pinia | 状态管理 |
| Vue Router | 路由 |
| Axios | REST 请求 |
| markdown-it | Markdown 渲染 |
| Vite | 构建工具 |

### 4.2 页面路由

**文件：** `frontend/src/router/index.ts`

| 路由 | 组件 | 功能 |
|------|------|------|
| `/` | ChatView.vue | 主聊天界面 |
| `/tools` | ToolsView.vue | 工具浏览 |
| `/skills` | SkillsView.vue | 技能管理 |
| `/agents` | AgentsView.vue | Agent 档案 |
| `/knowledge` | KnowledgeView.vue | 知识库 |
| `/settings` | SettingsView.vue | LLM 设置 |

### 4.3 开发代理

**文件：** `frontend/vite.config.ts`

```javascript
proxy: {
  '/api': { target: 'http://localhost:8000' },
  '/ws':  { target: 'ws://localhost:8000', ws: true }
}
```

前端 `localhost:3000` 的请求自动代理到后端 `:8000`。

---

## 5. Chat Store 事件处理

**文件：** `frontend/src/stores/chat.ts`

```typescript
// 核心状态
const messages = ref<ChatMessage[]>([])
const isLoading = ref(false)
const sessionId = ref('session_' + Date.now())
const ws = ref<ChatWebSocket | null>(null)

// 事件处理摘要
ws.on('start',       () => { isLoading = true })
ws.on('reasoning',   (data) => { 更新 streaming 消息 content })
ws.on('tool_call',   (data) => { 追加 tool_calls 条目 })
ws.on('tool_result', (data) => { 更新对应 tool 的 result })
ws.on('final',       (data) => { 设置最终 output，停止 streaming })
ws.on('done',        () => { isLoading = false })
ws.on('error',       (data) => { 显示错误消息 })
```

### 5.1 ChatMessage 结构

```typescript
interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  tool_calls?: { tool: string; result: string }[]
  timestamp: number
  isStreaming?: boolean
}
```

### 5.2 发送消息

```typescript
function sendMessage(input: string, mode: string, skill: string | null) {
  // 1. 添加用户消息到 messages
  // 2. 添加空的 assistant 消息（isStreaming=true）
  // 3. WebSocket 发送 JSON
  ws.send({
    type: 'message',
    input,
    mode,
    skill,
    provider: 'deepseek',
    temperature: 0.7,
  })
}
```

---

## 6. ChatView 界面功能

**文件：** `frontend/src/views/ChatView.vue`

| 功能 | 说明 |
|------|------|
| 消息列表 | 用户/助手消息，Markdown 渲染 |
| 工具调用展示 | 显示 tool_call 名称和结果 |
| 模式选择器 | adaptive / reasoning_action / task_orchestration / collaborative_decision |
| 技能选择器 | 激活 financial_audit 等技能 |
| 快捷操作 | 预设 demo 问题一键发送 |
| 流式输出 | reasoning 事件实时更新消息内容 |
| 清除会话 | 调用 DELETE /api/sessions/{id} |

---

## 7. 其他页面

### ToolsView
- 调用 `GET /api/tools`
- 卡片展示每个工具的名称、描述、分类

### SkillsView
- 调用 `GET /api/skills`
- 激活/停用技能按钮

### AgentsView
- 调用 `GET /api/agents` + `GET /api/catalog`
- 展示 Agent 档案和执行模式说明

### KnowledgeView
- 上传：`POST /api/knowledge/upload`（multipart form）
- 搜索：`POST /api/knowledge/search`
- 统计：`GET /api/knowledge/stats`

### SettingsView
- 读取/更新 LLM Provider 配置
- **注意：** 当前 Chat 未完全使用 Settings 中的 Provider 选择

---

## 8. 答辩演示 UI 操作

### 推荐演示路径

```
1. 打开 localhost:3000
2. Tools 页 → 展示 10 个工具（30 秒）
3. Chat 页 → 选择 adaptive 模式
4. 发送简单问题 → 展示 ReAct 工具调用（1 分钟）
5. 激活 financial_audit → 粘贴 JSON → 展示审计流水线（3 分钟）
6. 切换 collaborative_decision → 发送辩论请求（3 分钟）
7. Knowledge 页 → 上传文档 → Chat 中提问（2 分钟）
```

---

## 9. 已知前端限制

| 限制 | 说明 |
|------|------|
| Provider 未打通 | Chat 固定发送 deepseek，Settings 切换不影响 Chat |
| thinking 事件 | handler 为空，未展示思考指示器 |
| intermediate 事件 | 仅追加斜体文本，未做结构化卡片 |
| Skills Execute | API 存在但 Skills 页未对接 |
| 会话列表 | GET /api/sessions 返回空数组 |

答辩时可主动说明这些是已知改进项，体现对项目的全面理解。

---

## 10. 常见问题

**Q: 为什么用 WebSocket 而不是 SSE？**  
A: WebSocket 双向通信，支持同一连接多轮对话，且事件类型更丰富。SSE 仅适合单向推送。

**Q: session_id 怎么管理？**  
A: 前端生成 `session_` + timestamp，同一页面会话共享。刷新页面会生成新 session。

**Q: 前端如何处理断线？**  
A: 当前为基础实现，断线后 isLoading 置 false。可扩展自动重连。

**Q: Markdown 渲染安全吗？**  
A: 使用 markdown-it 默认渲染，demo 场景足够。生产环境需 XSS 过滤。

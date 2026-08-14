# PRD v2.0 — 会计学通用工作台业务完善

> 版本：2.0  
> 日期：2026-07-24  
> 状态：已批准，进入开发  
> 目标：将 MVP 演示系统完善为**业务闭环可交付**的会计学通用工作台

---

## 1. 背景与目标

### 1.1 背景

当前系统已具备 ReAct 对话、技能编排、知识检索、多 Agent 辩论等核心能力，但存在：

- 设置页与聊天行为不一致（Provider 固定 DeepSeek）
- 知识库只能粘贴文本，无法管理文档生命周期
- 会话无历史、RAG 无引用展示、过程不可解释
- 配置不持久化、基础设施状态不可见
- 缺少基础认证、审计与导出能力

### 1.2 产品目标

| 维度 | 目标 |
|------|------|
| 可信 | 模型配置真实生效；答案展示知识引用；过程结构化可见 |
| 可管 | 知识文档 CRUD；技能试跑；会话列表与恢复 |
| 可运营 | 系统健康面板；Token 统计；操作审计；报告导出 |
| 可交付 | 配置持久化；Docker 跨平台；Agent 超时；代码执行限时 |

### 1.3 不在本次范围

- 多租户 SaaS 计费
- 完整 RBAC 权限矩阵
- LangGraph 引擎替换
- 生产级代码沙箱（Docker 隔离）

---

## 2. 用户角色

| 角色 | 描述 | 核心诉求 |
|------|------|---------|
| 业务用户 | 财务/分析人员 | 对话、技能、知识检索、导出报告 |
| 管理员 | 平台配置人员 | 模型接入、系统状态、审计日志 |
| 访客 | 未登录 | 仅可访问健康检查（可选启用登录门禁） |

---

## 3. 功能需求

### 3.1 模型与接入（FR-01）

**现状问题**：聊天固定 DeepSeek，设置页修改无效，重启丢失。

**需求**：

1. 聊天 WebSocket 必须读取客户端传入的 `provider`、`model`、`temperature`
2. 未传时使用 `default_provider`（可在设置页修改并持久化）
3. `PUT /api/settings/llm` 写入 `data/settings.json`，启动时合并 `.env`
4. `GET /api/settings/llm` 返回 `has_api_key`、`temperature`、`max_tokens`
5. `PUT /api/settings/llm/default` 修改默认 Provider

**验收**：

- [ ] 设置页选 OpenAI 后，聊天实际调用 OpenAI 配置
- [ ] 重启后端后 Provider 配置仍保留

---

### 3.2 智能对话（FR-02）

**需求**：

1. **RAG 引用**：检索到知识后，WS 推送 `citation` 事件，前端展示引用卡片
2. **结构化步骤**：Plan-Execute / 辩论推送 `step` 事件，前端时间线展示
3. **思考状态**：`thinking` 事件展示加载指示
4. **Token 用量**：`final` 事件含 `tokens_used`
5. **超时控制**：超过 `AGENT_TIMEOUT_SECONDS` 返回 error 并 done
6. **报告导出**：前端支持将 assistant 消息导出 Markdown

**验收**：

- [ ] 上传知识后对话，界面显示引用来源
- [ ] 120s 超时返回明确错误
- [ ] final 含 tokens_used 字段

---

### 3.3 会话管理（FR-03）

**需求**：

1. `GET /api/sessions` 返回活跃会话列表（id、title、message_count、updated_at）
2. `GET /api/sessions/{id}/messages` 返回标准 role（user/assistant）
3. `PATCH /api/sessions/{id}` 支持重命名
4. `DELETE /api/sessions/{id}` 清除短期+长期+情景记忆
5. 前端 Chat 页左侧会话列表，点击切换 session_id

**验收**：

- [ ] 新建对话出现在列表
- [ ] 切换会话加载历史消息
- [ ] 清空同时清除 Neo4j 情景数据

---

### 3.4 知识资产（FR-04）

**需求**：

1. `POST /api/knowledge/upload` 支持 JSON 文本（现有）+ `POST /api/knowledge/upload/file` 支持 txt/md/csv
2. `GET /api/knowledge/documents` 分页列表
3. `DELETE /api/knowledge/{doc_id}` 删除向量+图谱
4. 上传响应展示 `entities` 列表（前端）
5. 图谱不可用时返回 `graph_available: false`

**验收**：

- [ ] 可上传 .txt 文件并检索
- [ ] 可删除文档
- [ ] 入库后展示实体标签

---

### 3.5 技能编排（FR-05）

**需求**：

1. 技能页增加「试跑」面板，调用 `POST /api/skills/{name}/execute`
2. `document_analysis`：固定流程 file_reader（若含路径）→ 摘要 LLM
3. `data_viz`：code_executor 生成 matplotlib 描述 + LLM 解读
4. 试跑结果展示工具链与输出

**验收**：

- [ ] 技能页可独立试跑并看到结果
- [ ] 文档分析技能有明确步骤输出

---

### 3.6 系统状态（FR-06）

**需求**：

1. `GET /health` 返回组件状态：chroma、neo4j、llm_providers
2. 任一关键组件 down 时 status=degraded
3. 前端顶栏/设置页展示状态徽章

**验收**：

- [ ] 关闭 Neo4j 后 health 显示 graph unavailable
- [ ] 前端显示对应警告

---

### 3.7 认证与审计（FR-07）

**需求**：

1. `POST /api/auth/login`（默认 admin / admin123，可配置）
2. `GET /api/auth/me`
3. 敏感操作写审计日志：`data/audit.log`（JSON Lines）
4. 前端登录页；`AUTH_ENABLED=true` 时未登录跳转登录
5. 默认 `AUTH_ENABLED=false` 保持本地开发体验

**验收**：

- [ ] 启用 AUTH 后未登录无法改设置
- [ ] 登录/配置变更有审计记录

---

### 3.8 基础设施（FR-08）

**需求**：

1. `docker-compose.yml` 使用相对路径 `./data/docker/...`
2. `code_executor` 使用线程池 + timeout 限制执行时间

**验收**：

- [ ] Linux/Mac/Windows 均可 docker compose up
- [ ] 超长代码执行返回 timeout 错误

---

## 4. API 变更摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 增强组件探测 |
| GET | `/api/system/status` | 前端状态面板 |
| POST | `/api/auth/login` | 登录 |
| GET | `/api/auth/me` | 当前用户 |
| PUT | `/api/settings/llm/default` | 默认 Provider |
| GET | `/api/sessions` | 会话列表 |
| PATCH | `/api/sessions/{id}` | 重命名 |
| GET | `/api/knowledge/documents` | 文档列表 |
| DELETE | `/api/knowledge/{doc_id}` | 删除文档 |
| POST | `/api/knowledge/upload/file` | 文件上传 |
| GET | `/api/audit/logs` | 审计日志（管理员） |

### WebSocket 新增事件

| type | data |
|------|------|
| `citation` | `{ citations: [{ doc_id, title, score, snippet, source }] }` |
| `step` | `{ step, title, content, status }` |

### WebSocket final 扩展

```json
{
  "output": "...",
  "tool_calls": [],
  "execution_time_ms": 1234,
  "tokens_used": 567,
  "provider": "deepseek",
  "model": "deepseek-chat"
}
```

---

## 5. 前端页面变更

| 页面 | 变更 |
|------|------|
| LoginView | 新增登录页 |
| App.vue | 系统状态条、认证守卫 |
| ChatView | 会话侧栏、引用卡片、步骤时间线、导出 |
| KnowledgeView | 文件上传、文档列表、删除、实体展示 |
| SkillsView | 试跑面板 |
| SettingsView | 默认 Provider、API Key 状态、系统状态 |
| SystemStatus | 新组件 |

---

## 6. 数据存储

| 文件 | 用途 |
|------|------|
| `data/settings.json` | LLM Provider 持久化 |
| `data/audit.log` | 审计日志 |
| `data/docker/chroma` | Chroma 数据 |
| `data/docker/neo4j` | Neo4j 数据 |

---

## 7. 开发顺序

```
Phase 1 — 后端核心（Provider/超时/Token/引用/会话/健康/持久化）
Phase 2 — 知识库 CRUD + 文件上传 + 图谱删除
Phase 3 — 技能流水线 + 试跑 API 对齐
Phase 4 — 认证 + 审计
Phase 5 — 前端全量对接
Phase 6 — Docker + code_executor 超时
```

---

## 8. 整体验收清单

- [ ] FR-01 ~ FR-08 全部通过
- [ ] `npm run build` 成功
- [ ] 后端 import 无错误
- [ ] 演示路径 1~6（README）均可走通

---

## 9. 维护

开发完成后更新 `REMAINING_WORK.md`，将已完成项标记 `[x]`。

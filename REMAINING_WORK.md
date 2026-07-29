# Agent Platform — 待修理 / 完善清单（以现有代码为准）

> 更新时间：2026-07-21  
> 范围：**只描述当前代码里仍不完整、未接线或存在 stub 的项**。  
> 不包含 ARCHITECTURE.md、README 等文档与实现差异问题。

---

## 优先级说明

| 级别 | 含义 |
|------|------|
| **P0** | 影响核心功能可用性或本地无法跑通 |
| **P1** | 功能已有骨架，但实现不完整 / 前后端未接通 |
| **P2** | 体验、API 补全、配置项未生效 |
| **P3** | 死代码清理、测试、安全加固 |

---

## P0 — 运行环境 / 依赖可用性

| ID | 模块 | 现状（代码） | 待修理 |
|----|------|--------------|--------|
| P0-1 | `memory/long_term.py` | 非 Docker Chroma 时 `_enabled=False`，`remember/recall` 直接空操作 | 本地 PersistentClient 下长期记忆不可用；需 Docker 或 `ENABLE_VECTOR_MEMORY=true` |
| P0-2 | `db/neo4j.py` | 连接失败时 `_available=False`，后续查询全返回 `[]`，仅 print 日志 | 图谱 / 情景记忆 / 入库实体关联在无 Neo4j 时静默失效；前端无「服务不可用」提示 |
| P0-3 | `docker-compose.yml` | Volume 写死 `F:/agent-platform-data/...` | macOS/Linux 上 compose 可能无法正常挂载数据目录 |
| P0-4 | `db/chroma.py` | HTTP 连接失败回退 PersistentClient | 知识库向量与长期记忆依赖 embedding；本地首次可能极慢或行为与 Docker 不一致 |

---

## P1 — Agent 引擎

### 当前实现（基线）

- 主路径：`runtime.run_react_loop()` — LangChain `bind_tools` + 手写 ReAct 循环
- `stream()` / `invoke()` 行为已统一
- Plan-Execute、Multi-Agent 辩论均已接工具与记忆

### 仍待完善

| ID | 文件 | 现状 | 待修理 |
|----|------|------|--------|
| A-1 | `core/config.py` | `agent.timeout_seconds=120` 已读取 | **全项目无引用**，Agent 执行无超时中断 |
| A-2 | `agent/base.py` | `AgentResponse.tokens_used` 字段存在 | **从未赋值** |
| A-3 | `agent/runtime.py` | `invoke_llm_with_tools()` 已定义 | **无任何调用方**（死代码） |
| A-4 | `agent/runtime.py` | ~~最终答案通过 `stream_text_as_reasoning()` 切块推送~~ | ✅ 已实现 LLM `astream` 真 token 流 + 降级假流式 |
| A-5 | `agent/plan_execute.py` | Evaluator 仅支持整轮 `needs_replan`，最多 1 次 | **无单步失败重试**；某步工具失败不会单独 retry |
| A-6 | `agent/plan_execute.py` | 规划 / 评估 prompt 为英文 | 与中文 UI 混用（非 bug，可统一语言） |
| A-7 | `requirements.txt` | 含 `langgraph`、`langgraph-checkpoint` | **`backend/app` 内零 import**，纯 unused 依赖 |

---

## P1 — Multi-Agent 辩论

| ID | 文件 | 现状 | 待修理 |
|----|------|------|--------|
| M-1 | `multi_agent/debate.py` | `DebateOrchestrator` 三个方法 `raise NotImplementedError` | 类**未被** `AccountingDebateTeam` 继承或使用 |
| M-2 | `debate_team.py` | ~~流式路径 yield 整段 content 或切块 REASONING~~ | ✅ 法官/终审与角色输出已接 `stream_llm_text_events` / `_llm_round_events` |
| M-3 | `debate_team.py` | `_parse_verdict_sections()` 从 markdown 抽 `key_findings` 等 | 依赖标题格式，解析不稳定时字段为空 |
| M-4 | `debate.py` | `DebateResult.key_findings / risks_identified / consensus_points` | 仅终审解析写入，**round 级别无结构化输出** |

---

## P1 — 技能系统

### 已实现（基线）

- `skills/executor.py`：`execute()`、财务审计工具流水线、ReAct 回退
- 激活后：`resolve_system_prompt()` + `get_langchain_tools()` 工具筛选
- API：`POST /api/skills/{name}/execute`

### 仍待完善

| ID | 文件 | 现状 | 待修理 |
|----|------|------|--------|
| S-1 | `skills/builtin/document_analysis.py` | `execute()` 走通用 `SkillExecutor` | **无**「先读文件再摘要」等固定编排 |
| S-2 | `skills/builtin/data_viz.py` | 同上 | **无**专用可视化流水线（仅依赖 ReAct 自发调工具） |
| S-3 | `skills/registry.py` | `unregister()` 已实现 | **无 HTTP API** |
| S-4 | `frontend/SkillsView.vue` | 仅 activate/deactivate | **未接** `/api/skills/{name}/execute` 试跑 |
| S-5 | `api/chat.py` + `orchestrator` | WS 传 skill 时 `activate()`，不传时 `deactivate()` | 与 Skills 页 activate 重复，逻辑分散（可收敛到 orchestrator 一处） |

---

## P1 — RAG / 知识库 / 记忆

### 已实现（基线）

- 聊天：`memory/manager.load_context()` → `HybridRetriever.retrieve_formatted()`
- 入库：`hybrid.add_knowledge()` 自动 `extract_entities` + Neo4j Document
- 保存：`save_context()` 自动实体抽取 + 长期/情景记忆
- API：`GET /stats`、`DELETE /api/sessions/{id}`

### 仍待完善

| ID | 文件 | 现状 | 待修理 |
|----|------|------|--------|
| R-1 | `rag/entity_extractor.py` | 规则 / 正则抽取 | 质量有限，专名、复杂实体易漏 |
| R-2 | `core/config.py` | `memory.episodic_max_events=20` | **未使用**，情景记忆无条数上限控制 |
| R-3 | `rag/vector_store.py` | `delete(doc_id)` 已实现 | **无** `DELETE /api/knowledge/{doc_id}` |
| R-4 | `rag/hybrid.py` | 入库时对实体列表相邻两两 `RELATED_TO` | 关系较随意，无语义 |
| R-5 | `api/knowledge.py` | upload 返回 `entities` | **KnowledgeView 未展示**抽取结果 |
| R-6 | `memory/episodic.py` | `recall_entities` / `recall_relations` / `get_session_topics` | 已实现但**无调用方** |
| R-7 | `memory/long_term.py` | `forget()` 单条删除 | **无调用方**（`forget_session` 已被 `clear_session_all` 使用） |
| R-8 | 聊天 UI | 后端已注入 RAG 上下文 | 前端**不展示**引用了哪些知识片段 |

---

## P2 — API / 后端

| ID | 端点 / 模块 | 现状 | 待修理 |
|----|-------------|------|--------|
| B-1 | `GET /api/sessions` | `chat.py` 固定 `{"sessions": []}` | 会话列表未实现 |
| B-2 | `GET /api/tools/{name}` | 404 时 `return ({...}, 404)` tuple | FastAPI 下可能**不是标准 HTTP 404** |
| B-3 | `PUT /api/settings/llm` | `LLMFactory.update_provider()` 只改内存 | **进程重启后丢失** |
| B-4 | `GET /api/settings/llm` | 不返回 api_key | 合理，但未返回 `has_api_key` 等状态字段 |
| B-5 | `tools/registry.py` | `register` / `unregister` 有实现 | **无** `POST/DELETE /api/tools` 动态注册 API |
| B-6 | `GET /health` | 仅 `{"status": "healthy"}` | 不检测 Chroma / Neo4j / DeepSeek 配置是否可用 |
| B-7 | `main.py` | CORS `allow_origins=["*"]` | 开发可用，无环境区分 |

---

## P2 — 前端（相对后端能力）

| ID | 文件 | 现状 | 待修理 |
|----|------|------|--------|
| F-1 | `ChatView.vue` + `chat.ts` | WS 固定 `provider=deepseek`，不传 `model` | Settings / Chat 的 Provider、Model 选择与聊天**未接通** |
| F-2 | `stores/chat.ts` | `thinking` 事件 handler 为空 | 无思考中 UI 反馈 |
| F-3 | `stores/chat.ts` | `intermediate` 仅追加 `_message_` 文本 | Plan / 辩论步骤展示不直观，无结构化卡片 |
| F-4 | `SkillsView.vue` | 无 execute 试跑 | 后端 API 已有，前端未用 |
| F-5 | `KnowledgeView.vue` | upload 成功只 alert | 未展示 `entities_extracted` / 实体列表 |
| F-6 | `SettingsView.vue` | 可改多 Provider 配置 | 与聊天 DeepSeek 固定策略不一致，易误导用户 |

---

## P2 — 工具系统

| ID | 文件 | 现状 | 待修理 |
|----|------|------|--------|
| T-1 | `tools/builtin/code_executor.py` | `exec()` 同进程，`timeout` 参数未使用 | 非隔离执行；长时间运行无法中断 |
| T-2 | `tools/base.py` | `requires_confirmation: bool = False` | 字段存在，**无确认流程** |
| T-3 | `tools/builtin/web_search.py` | 依赖 `duckduckgo-search` | ImportError 时仅返回错误字符串，无降级策略 |

---

## P3 — 死代码 / 未使用符号

| 文件 | 项 |
|------|-----|
| `agent/runtime.py` | `invoke_llm_with_tools` |
| `multi_agent/debate.py` | `DebateOrchestrator` 整类 |
| `models/chat.py` | `ChatResponse`, `SessionInfo`（若存在且未引用） |
| `memory/episodic.py` | `recall_entities`, `recall_relations`, `get_session_topics` |
| `memory/long_term.py` | `forget()` |
| `memory/manager.py` | `as_runnable()` 无调用方 |
| `rag/hybrid.py` | `as_runnable()` 无调用方 |
| `skills/base.py` | 未使用的 `SystemMessage`, `HumanMessage` import |
| `requirements.txt` | `langgraph`, `langgraph-checkpoint` |

---

## P3 — 测试（当前为零）

| 建议补测 | 覆盖点 |
|----------|--------|
| `entity_extractor.extract_entities` | 中英文、JSON 共存文本 |
| `HybridRetriever._rrf_fusion` | 排序与去重 |
| `SkillExecutor.run_financial_audit_pipeline` | mock 工具链 |
| `run_react_loop` | mock LLM tool_calls 循环 |
| `memory/manager.load_context` | strategy 开关 |
| WebSocket 消息序列 | event type 契约 |

---

## P3 — 安全（生产向，面试 demo 可暂缓）

| 项 | 说明 |
|----|------|
| `code_executor` | 任意 Python 执行 |
| WebSocket | 无鉴权、无 rate limit |
| compose / 默认 config | Neo4j 密码明文 |
| CORS | 全开放 |

---

## 建议修理顺序（按代码价值）

```
1. P0-3  docker-compose 路径（否则本地 infra 不稳定）
2. P0-1  长期记忆本地策略（或明确仅 Docker 模式）
3. B-6    /health 探测 Chroma/Neo4j（便于排查 P0-2）
4. S-4 + F-4  Skills execute 试跑 UI
5. R-5 + F-5  Knowledge 上传展示 entities
6. A-1    Agent 超时 enforcement
7. B-3    Settings 持久化
8. M-1    删除或接入 DebateOrchestrator
9. P3     死代码与 langgraph 依赖清理
```

---

## 当前能力 — 代码层面可靠度

| 能力 | 可靠度 | 代码条件 |
|------|--------|----------|
| ReAct 聊天 + 工具调用 | 高 | 需 `DEEPSEEK_API_KEY` |
| 技能 Prompt + 工具筛选 | 高 | WS 传 `skill` 或先 activate |
| 财务审计流水线 | 高 | 输入含财务 JSON |
| Plan-Execute 分步 + 重规划 | 中高 | 慢；无单步 retry |
| Multi-Agent 辩论 + 工具 | 中 | 慢；块级流式 |
| 知识库 upload + search API | 中 | Chroma 可用 |
| 聊天 RAG 注入 | 中 | 先 upload；Chroma 可用 |
| 图谱检索 / 情景记忆 | 低~中 | **必须 Neo4j 可用** |
| 长期跨会话记忆 | 低~中 | Docker Chroma 或 `ENABLE_VECTOR_MEMORY=true` |
| Settings 改配置生效 | 中 | 仅当次进程；聊天仍 DeepSeek |
| 动态注册工具 | 无 | registry 有代码，无 API |

---

## 已完成（代码已实现，勿重复修）

### Agent
- [x] `stream` / `invoke` 统一 ReAct 工具循环（`runtime.run_react_loop`）
- [x] Plan-Execute：plan → execute → evaluate → replan → aggregate + 流式 intermediate
- [x] Orchestrator 模式路由 + 固定 DeepSeek
- [x] 辩论团队工具执行 + `save_context`
- [x] WebSocket → `TOOL_CALL` / `TOOL_RESULT` / `FINAL` 事件链

### 技能
- [x] 三技能 `execute()` + `SkillExecutor`
- [x] 财务审计逐步调工具 + LLM 报告
- [x] `get_system_prompt` / `get_context_strategy` 接入 Agent 与 Memory
- [x] `POST /api/skills/{name}/execute`

### RAG / 记忆
- [x] 聊天 load_context 接 HybridRetriever
- [x] upload 自动实体 + Document 节点
- [x] save_context 自动实体 + 三层写入
- [x] `GET /api/knowledge/stats`（vector + graph 计数）
- [x] `DELETE /api/sessions/{id}` + 前端 clearChat 调用

---

## 维护方式

完成某项后，将 `- [ ]` 改为 `- [x]`，并注明日期。  
本清单仅跟踪**代码实现缺口**，文档类问题 intentionally 不包含。

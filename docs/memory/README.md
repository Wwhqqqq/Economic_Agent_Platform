# 记忆模块

## 模块职责

记忆模块解决的核心问题是：**Agent 如何在多轮对话中「记住」有用信息，并在新问题时召回相关上下文**。本平台采用「三层记忆 + 知识库 RAG」的统一编排方案，由 `MemoryManager` 作为唯一对外入口，Agent 运行时无需关心各层存储细节。

设计理念借鉴认知心理学中的记忆分层：

- **短期记忆** ≈ 工作记忆：当前会话的最近对话
- **长期记忆** ≈ 语义记忆：跨会话的重要片段，向量相似度召回
- **情景记忆** ≈ 情节与关联：谁说了什么、涉及哪些实体、实体间关系

此外，**知识库 RAG** 虽不属于「对话记忆」，但在上下文加载阶段与记忆层合并注入，用户感知上同属「Agent 记得的内容」。

## 三层记忆详解

### 第一层：短期记忆（ShortTermMemory）

**存储介质**：Python 进程内存，字典结构 `session_id → 消息列表`。

**写入时机**：每轮对话结束后，同步追加 user 消息与 assistant 最终回复。

**读取方式**：按 token 估算做滑动窗口截断，保留最近若干条消息（默认上限 `SHORT_TERM_MEMORY_MAX_TOKENS = 4000`）。注入 Prompt 时转为 LangChain `BaseMessage` 列表。

**附加能力**：
- 会话元数据：标题（首条用户消息截取）、创建/更新时间
- 会话列表 API：供前端侧边栏展示历史对话
- 重命名、删除：删除时联动清理长期与情景层中该 session 的数据

**特点**：速度最快，但进程重启后丢失；适合「当前对话连贯性」。

### 第二层：长期记忆（LongTermMemory）

**存储介质**：ChromaDB 独立集合 `long_term_memory`。

**写入时机**：每轮对话结束后，**异步后台任务**将 user + assistant 合并文本写入，附带 importance 分数（0.5–0.7 区间，由内容长度与是否含数字等启发式决定）。

**读取方式**：用当前用户问题做语义检索，取 top-K（默认 5）条历史片段，格式化为「Relevant Past Knowledge」段落注入系统 Prompt。

**启用条件**：
- 连接 Docker 远程 Chroma 时**自动启用**
- 本地 PersistentClient 模式下**默认关闭**（避免首次启动下载 embedding 模型）
- 可通过 `ENABLE_VECTOR_MEMORY=true` 强制开启

**超时保护**：召回操作 5 秒超时，失败则跳过，不影响主链路。

**特点**：跨会话、跨重启持久化；适合「用户上周问过类似问题」的场景。

### 第三层：情景记忆（EpisodicMemory）

**存储介质**：Neo4j 图数据库。

**图模型**（简化）：
- `Conversation` 节点：对应 session
- `Message` 节点：单条消息，关联到 Conversation
- `Entity` 节点：从文本中提取的实体（公司名、财务指标等）
- `Document` 节点：知识库文档（与 RAG 模块共享）
- 关系：`HAS_MESSAGE`、`MENTIONS`、`RELATED_TO` 等

**写入时机**：异步后台，每轮对话后：
1. 规则提取实体（见 RAG 模块的 entity_extractor）
2. 创建/更新 Message 节点
3. 将实体与 Conversation 关联
4. 共现实体之间建立 RELATED_TO 边

**读取方式**：从用户输入提取关键词 → 在图谱中查找相关实体及其一跳关系 → 格式化为三元组文本（如「A --[关系]--> B」）注入 Prompt。

**降级策略**：Neo4j 不可用时，所有写/read 操作静默跳过，不抛异常。

**特点**：擅长表达「某概念与某文档/某历史事件有关联」，补足纯向量检索的结构化不足。

## MemoryManager 统一编排

### 上下文加载（load_context_bundle）

Agent 启动 ReAct 循环前调用。按以下顺序拼接系统 Prompt 各段落：

1. **基础系统 Prompt**（来自技能 + Agent 配置）
2. **知识库 RAG**（若 `include_knowledge=true`）— 调用 HybridRetriever 混合检索
3. **长期记忆召回**（若 `include_long_term=true`）
4. **情景图谱上下文**（若 `include_entities=true` 且输入足够长）
5. **短期对话历史**（条数由 `max_history` 控制，默认 10）

返回结构 `{ context: str, citations: list }`。citations 供前端展示引用卡片，后端以 `CITATION` 事件推送。

**策略来源**：默认全开；激活技能时改用技能的 `get_context_strategy()`，例如财务审计技能可能提高 `max_history`、确保开启知识库检索。

**超时**：整段加载 5 秒超时，任一层失败仅打印日志并跳过。

### 上下文保存（save_context）

1. **同步**：短期记忆追加消息
2. **异步**（asyncio.create_task）：
   - 长期记忆 `remember()`，文本截断至 1200 字符
   - 情景记忆 `log_event()`，含实体提取

这种「读同步、写异步」设计保证用户感知延迟主要来自 LLM，而非数据库 IO。

## 与 RAG 模块的边界

| 维度 | 知识库 RAG | 长期记忆 |
|------|-----------|----------|
| Chroma 集合 | `knowledge_base` | `long_term_memory` |
| 数据来源 | 用户主动上传文档 | 对话自动生成 |
| 检索触发 | 每次用户提问 | 每次用户提问 |
| 典型内容 | 制度文件、报表说明 | 「上次讨论过 ROE 下降原因」 |

两者在 MemoryManager 中串联加载，但存储与生命周期完全隔离。

## 会话生命周期

```
新建会话（前端生成 session_id）
    → WebSocket 连接
    → 多轮 load_context + save_context
    → 用户「清空会话」或「删除会话」
        → 短期：清空消息列表
        → 长期：按 session 元数据过滤删除（若实现）
        → 情景：删除 Conversation 子图
```

## 配置项

| 环境变量 | 默认值 | 作用 |
|----------|--------|------|
| `SHORT_TERM_MEMORY_MAX_TOKENS` | 4000 | 短期记忆 token 窗口 |
| `LONG_TERM_MEMORY_TOP_K` | 5 | 长期记忆召回条数 |
| `EPISODIC_MEMORY_MAX_EVENTS` | 20 | 情景记忆事件上限（配置项，部分路径未严格 enforcement） |
| `ENABLE_VECTOR_MEMORY` | auto | 本地/远程 Chroma 下是否启用向量记忆 |
| `VECTOR_MEMORY_TIMEOUT` | 5 | 向量操作超时秒数 |

## 代码位置

| 文件 | 职责 |
|------|------|
| `backend/app/memory/manager.py` | 统一编排入口 |
| `backend/app/memory/short_term.py` | 会话内消息存储 |
| `backend/app/memory/long_term.py` | Chroma 跨会话记忆 |
| `backend/app/memory/episodic.py` | Neo4j 情景图谱 |
| `backend/app/db/chroma.py` | Chroma 客户端（HTTP / 本地双模式） |
| `backend/app/db/neo4j.py` | Neo4j 客户端与降级逻辑 |

## 设计权衡与已知限制

- **全局技能状态**：激活技能是进程级单例，并发多会话可能互相影响记忆策略（同一时刻只有一个 active_skill）。
- **实体提取为规则式**：非 LLM 抽取，对复杂指代可能遗漏；详见 RAG 模块。
- **长期记忆本地默认关**：开发机不启 Docker 时，跨会话记忆能力不可用，需在文档/demo 中说明。

## 相关文档

- [RAG 模块](../rag/README.md) — 知识库检索与入库
- [技能模块](../skills/README.md) — context_strategy 如何覆盖记忆策略
- [Agent 编排](../agent-orchestration/README.md) — 何时触发 load/save

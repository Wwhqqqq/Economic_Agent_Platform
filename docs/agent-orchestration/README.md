# Agent 编排模块

## 模块职责

Agent 编排模块是整个平台的**执行中枢**。它负责：接收用户输入 → 选择执行模式 → 调度合适的 Agent → 驱动 ReAct 工具循环 → 流式输出事件 → 触发记忆持久化。

用户不需要直接与 ReAct 循环打交道，只需在聊天页选择「自适应 / 推理行动 / 任务编排 / 协同决策」，编排器会在背后完成 Agent 选择与生命周期管理。

## 核心组件

### 1. AgentOrchestrator（调度编排器）

全局单例，是对外统一入口。主要职责：

- **模式规范化**：将前端传入的模式字符串（含 legacy 别名如 `react`、`multi_agent`）转换为内部规范 key。
- **智能路由**：当模式为 `adaptive` 时，扫描用户输入关键词，自动选择 ReAct、Plan-Execute 或辩论团队。
- **Agent 实例化**：根据选定模式返回对应 Agent 实例。ReAct 与 Plan-Execute 为常驻单例；辩论团队每次请求新建实例。
- **流式包装**：在 Agent 执行前后发送 `START` 事件，附带 execution_mode、active_skill、session_id 等元信息。

### 2. BaseAgent 与事件模型

所有 Agent 继承 `BaseAgent` 抽象基类，统一实现 `invoke()`（同步收集完整响应）和 `stream()`（异步迭代事件流）两种接口。

**AgentEvent** 是模块对外的「直播信号」，主要事件类型包括：

| 事件类型 | 含义 | 前端典型表现 |
|----------|------|-------------|
| `START` | 任务开始 | 进入 loading 状态 |
| `THINKING` | 模型正在推理 | 显示「思考中」动画 |
| `TOOL_CALL` | 发起工具调用 | 展示工具名与参数 |
| `TOOL_RESULT` | 工具返回结果 | 更新工具卡片结果区 |
| `REASONING` | 流式文本输出 | Markdown 逐字渲染 |
| `CITATION` | 引用来源 | 展示知识库引用卡片 |
| `STEP` | 计划步骤进度 | Plan-Execute 的步骤时间线 |
| `INTERMEDIATE` | 中间产物 | 计划 JSON、评估结果等 |
| `FINAL` | 最终答案 | 定稿内容与 token 统计 |
| `DONE` | 全流程结束 | 关闭 loading，刷新会话列表 |

这种事件驱动设计使同一套后端逻辑能同时服务 WebSocket 流式 UI 和 REST 同步调用。

### 3. ReAct Agent（推理 + 行动）

**适用场景**：大多数日常问答、单次或少量工具调用、技能激活后的对话。

**执行逻辑**（`runtime.run_react_loop`）：

1. **配置规范化**：合并 session_id、provider、temperature、max_iterations 等参数；默认 provider 来自环境变量 `DEFAULT_LLM_PROVIDER`。

2. **Prompt 组装**：
   - 若存在激活技能，优先使用技能的系统 Prompt，再叠加 Agent 默认 Prompt。
   - 调用 `MemoryManager.load_context_bundle()`，将 RAG 结果、长期记忆、图谱信息、短期历史注入系统消息。

3. **工具绑定**：从 `ToolRegistry` 取出 LangChain 格式的工具列表。若技能处于激活状态，仅暴露技能声明的 `required_tools` 子集。

4. **ReAct 循环**（最多 `AGENT_MAX_ITERATIONS` 次，默认 10）：
   - 向 LLM 发送当前消息列表（含历史 tool_call / tool_result）。
   - 若模型返回 `tool_calls`：逐个执行工具，将结果封装为 `ToolMessage` 追加到上下文，继续下一轮。
   - 若模型返回纯文本：通过 LLM **`astream` 真 token 流** 推送 `REASONING` 事件，退出循环（失败时降级为切块假流式）。

5. **收尾**：可选地将本轮 user/assistant 消息写入记忆；发送 `FINAL` 与 `DONE` 事件。

**流式配置**：环境变量 `AGENT_STREAMING_ENABLED`（默认 `true`）、`AGENT_STREAM_FALLBACK_CHUNK_SIZE`（默认 `24`）。详见 [LLM 真流式输出 PRD](./prd/LLM真流式输出-PRD.md)。

**设计要点**：这是典型的 LangChain ReAct 模式，但实现为显式 Python 循环而非 LangGraph 状态图，便于调试和自定义事件流。

### 4. Plan-Execute Agent（先规划后执行）

**适用场景**：需要拆解的多步骤任务，如「对某公司做完整财务审计并出具报告」。

**五阶段流水线**：

```
用户任务
   │
   ▼
① Plan（规划）── LLM 输出 JSON 步骤列表（overview + steps）
   │
   ▼
② Execute（逐步执行）── 每个 step 独立跑一轮 ReAct（不单独写记忆）
   │
   ▼
③ Evaluate（评估）── LLM 判断结果是否充分，是否需要 replan
   │
   ▼
④ Replan（可选，最多 1 次）── 根据评估反馈重新规划并执行
   │
   ▼
⑤ Aggregate（汇总）── ReAct 将所有步骤结果综合成最终报告，写入记忆
```

**与 ReAct 的区别**：

- Plan-Execute 在步骤级嵌套 ReAct，子步骤的 `persist_memory=False`，避免污染会话历史。
- 流式输出包含 `INTERMEDIATE` 和 `STEP` 事件，前端可展示「计划 → 执行 → 评估」时间线。
- 规划与评估阶段使用较低 temperature（0.3），提高 JSON 结构稳定性。

**容错**：若 LLM 返回的 plan 不是合法 JSON，会 fallback 为「单步执行整个任务」。

### 5. Runtime 运行时（共享引擎）

`runtime.py` 是 ReAct、Plan-Execute、多 Agent 角色共用的底层引擎，核心能力包括：

- **LLM 创建**：委托 `LLMFactory.create()`，支持运行时 override provider/model。
- **工具执行**：解析 LLM 的 tool_call，查注册中心，执行 `tool.execute(**args)`，将 `ToolResult` 转为字符串回填。
- **上下文加载**：统一入口 `load_agent_context()`，超时 10 秒，超时则跳过外部记忆/RAG。
- **Prompt 工具循环**：`run_prompt_tool_loop()` 供多 Agent 角色使用——给定一段 HumanMessage prompt，跑完整 ReAct 后返回文本与 tool_calls 列表。

## 与其他模块的协作

```
AgentOrchestrator
    │
    ├─► SkillRegistry ── 决定 Prompt 前缀、工具子集、记忆策略
    │
    ├─► MemoryManager ── 读：上下文组装；写：对话结束后持久化
    │
    ├─► ToolRegistry ── ReAct 循环中动态调用
    │
    ├─► LLMFactory ── 创建 ChatOpenAI / ChatAnthropic 实例
    │
    └─► AccountingDebateTeam（协同决策模式）── 见 multi-agent 文档
```

## 配置项

| 环境变量 | 默认值 | 作用 |
|----------|--------|------|
| `AGENT_MAX_ITERATIONS` | 10 | ReAct 最大工具调用轮数 |
| `AGENT_TIMEOUT_SECONDS` | 120 | WebSocket 单次请求超时 |
| `DEFAULT_LLM_PROVIDER` | deepseek | 默认大模型 Provider |
| `DEBATE_MAX_ROUNDS` | 3 | 辩论模式最大轮数（归属 multi-agent） |

## 代码位置

| 文件 | 职责 |
|------|------|
| `backend/app/agent/orchestrator.py` | 编排器入口 |
| `backend/app/agent/runtime.py` | ReAct 循环与共享运行时 |
| `backend/app/agent/react_agent.py` | ReAct Agent 封装 |
| `backend/app/agent/plan_execute.py` | Plan-Execute Agent |
| `backend/app/agent/base.py` | 基类、事件、响应模型 |
| `backend/app/core/catalog.py` | 执行模式与 Agent 档案元数据 |

## 使用建议

- **简单问答**：使用「推理行动」或「自适应」，延迟最低。
- **结构化长任务**：显式选择「任务编排」，或输入含「审计、分析报告」等关键词触发自动路由。
- **观点碰撞与风控评审**：选择「协同决策」，适合财务争议、投资评审类演示。

## 相关文档

- [执行模式详解](./02-执行模式详解.md) — 智能路由 / 推理闭环 / 任务编排 / 协同决策 与 ReAct / Plan-Execute / Multi-Agent 对照
- [LLM 真流式输出 PRD](./prd/LLM真流式输出-PRD.md) — Token 级流式改造需求（待评审）
- [记忆模块](../memory/README.md) — 上下文如何被注入
- [技能模块](../skills/README.md) — 如何改变 Agent 行为
- [多 Agent 模块](../multi-agent/README.md) — 协同决策模式详解

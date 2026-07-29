# PRD — LLM 真流式输出（Token Streaming）

> **版本**：1.0  
> **日期**：2026-07-29  
> **状态**：已实现（v1.0，2026-07-29）  
> **优先级**：P1（体验增强）  
> **关联模块**：Agent 编排 / WebSocket 聊天 / 前端 ChatView  
> **关联文档**：[执行模式详解](../02-执行模式详解.md)、[Agent 编排 README](../README.md)、[API 与前端交互](../../defense/08-API与前端交互.md)

---

## 1. 背景与目标

### 1.1 背景

当前聊天页的「流式输出」与 WorkBuddy、ChatGPT 等产品的体验存在明显差距：

| 维度 | 竞品（WorkBuddy 等） | 当前实现 |
|------|---------------------|----------|
| 文本出现时机 | 模型 **生成过程中** 逐 token 显示 | 模型 **整段生成完毕** 后才出现 |
| 实现方式 | LLM API `stream=true` / SSE | `llm.ainvoke()` 等待全文 → `stream_text_as_reasoning()` 按 24 字切块回放 |
| 工具调用期间 | 展示工具状态，正文暂停 | 长时间仅「正在思考…」，无正文 |
| 用户感知 | 打字机效果，低延迟 | 长时间空白 → 文字快速涌出或一次性出现 |

**代码现状（已核实）：**

```python
# backend/app/agent/runtime.py
response = await llm_with_tools.ainvoke(messages)   # 阻塞至整轮结束
final_output = message_content(response)
async for event in stream_text_as_reasoning(final_output):  # chunk_size=24 假流式
    yield event
```

前端 `chat.ts` 已监听 `reasoning` 事件并支持 `token` / `accumulated` 增量更新，**前端协议基本就绪**，瓶颈在后端未使用 LLM 原生流式 API。

`REMAINING_WORK.md` 已记录为 **A-4**：非 LLM 真 token 流。

### 1.2 产品目标

| 目标 | 说明 | 可度量 |
|------|------|--------|
| **真流式** | 最终回答在 LLM 生成过程中实时推送至聊天区 | 首 token 延迟（TTFT）< 3s（正常网络 + DeepSeek） |
| **体验对齐** | 用户可见「逐字/逐词」打字机效果，接近 WorkBuddy | 用户主观验收 + 录屏对比 |
| **兼容现有协议** | 不破坏 WebSocket 事件模型；旧前端仍能工作 | 事件字段向后兼容 |
| **全模式覆盖** | ReAct / Plan-Execute 汇总 / 多 Agent 角色输出均支持 | 见 §6 分阶段范围 |
| **可降级** | Provider 不支持流式或流式失败时，回退现有假流式 | 降级路径可测 |

### 1.3 不在本次范围

- 规划/评估阶段 JSON 的 token 级流式（Plan-Execute 的 Plan/Evaluate prompt 仍一次性返回 JSON）
- 工具内部执行过程的流式（工具结果是整块返回）
- 将 ReAct 循环改为 LangGraph 状态图（`langgraph` 依赖仍不引入）
- 新增 SSE/HTTP 流式聊天接口（继续沿用 WebSocket）
- 打字机光标、Markdown 增量渲染性能优化（可作为 P2 跟进，非阻塞上线）
- 离线/mock 流式演示模式

---

## 2. 用户与场景

### 2.1 目标用户

使用聊天页的所有用户（普通用户、会员），尤其是：

- 需要长时间阅读模型生成报告的用户
- 对「等待焦虑」敏感、希望即时反馈的用户
- 答辩/demo 场景下的演示者

### 2.2 核心场景

| 编号 | 场景 | 当前体验 | 期望体验 |
|------|------|----------|----------|
| **S1** | 推理闭环模式，简单问答（不触发工具） | 等待数秒 → 文字快速涌出 | 问题发出后 1–3s 内开始逐字显示回答 |
| **S2** | 推理闭环模式，需调用 1–2 个工具 | 长时间「思考中」→ 工具卡片 → 再等待 → 全文涌出 | 工具阶段显示工具 UI；**最终回答**仍逐 token 流式 |
| **S3** | 任务编排模式，多步执行后汇总 | 仅步骤事件，汇总阶段假流式 | 汇总报告逐 token 流式；各步骤结果可选择性流式（Phase 2） |
| **S4** | 协同决策模式，分析师/质疑者/裁判发言 | 角色阶段长时间无正文 | 各角色 **最终发言** 逐 token 流式 |
| **S5** | 流式过程中用户切换会话 | — | 当前会话流式中断，不污染其他会话 |
| **S6** | Provider 流式 API 失败 | — | 自动降级为假流式，用户仍能看到完整回答，Console 记 warn |

---

## 3. 术语定义

| 术语 | 定义 |
|------|------|
| **真流式（Token Streaming）** | 调用 LLM `astream` / `astream_events`，每收到一个 content delta 即推送前端 |
| **假流式（Simulated Streaming）** | 现有 `stream_text_as_reasoning()`，全文到手后按固定 chunk 切块推送 |
| **TTFT** | Time To First Token，从用户发送到聊天区出现第一个字符的时间 |
| **工具轮（Tool Round）** | ReAct 循环中 LLM 返回 `tool_calls`、执行工具、等待下一轮的一整轮 |
| **正文流（Answer Stream）** | 仅指 LLM 输出自然语言正文；不含工具参数 JSON |

---

## 4. 功能需求

### 4.1 后端 — ReAct 主循环（P0，必须）

**文件**：`backend/app/agent/runtime.py` → `run_react_loop()`

| ID | 需求 | 说明 |
|----|------|------|
| **F-B1** | 最终回答轮使用 `astream` | 当 LLM 本轮输出为纯文本（无 `tool_calls`）时，逐 chunk 推送 `REASONING` |
| **F-B2** | 工具轮保持 `ainvoke` 或 `astream` 聚合 | 检测到 `tool_calls` 时停止正文流，执行工具，进入下一轮；行为与现网一致 |
| **F-B3** | 事件 payload 兼容 | 每个 chunk 推送 `{ "token": "<delta>", "accumulated": "<全文-so-far>" }` |
| **F-B4** | `FINAL` 事件保留 | 流式结束后仍发送 `FINAL`，`output` 为完整文本（供记忆持久化、导出） |
| **F-B5** | 尊重 `AgentConfig.streaming` | `streaming=False` 时走现有 `ainvoke` + 假流式/直接 FINAL |
| **F-B6** | 流式失败降级 | `astream` 异常时 fallback：`ainvoke` → `stream_text_as_reasoning()`，并 log warning |

**ReAct 循环伪代码（评审用）：**

```
for iteration in 1..max_iterations:
    yield THINKING

    if config.streaming:
        async for chunk in llm_with_tools.astream(messages):
            累积 chunk → 判断是否含 tool_calls
            if 出现 tool_calls:
                停止流式 → 执行工具 → continue 外层循环
            if 出现 content delta:
                yield REASONING { token, accumulated }

        若本轮为纯文本 → break
    else:
        response = await ainvoke(...)
        ... 现有逻辑 ...

yield FINAL { output: accumulated_text, ... }
yield DONE
```

### 4.2 后端 — Plan-Execute（P1，第二阶段）

**文件**：`backend/app/agent/plan_execute.py`

| ID | 需求 | 说明 |
|----|------|------|
| **F-P1** | Plan / Evaluate 阶段不变 | 仍 `ainvoke` 期望 JSON，不流式 |
| **F-P2** | 汇总阶段（Aggregate）真流式 | `run_react_loop` 升级后自动受益 |
| **F-P3** | 单步 Execute 真流式 | 子步骤最终输出逐 token 推送（经 `run_react_loop`） |
| **F-P4** | 步骤事件不变 | `STEP` / `INTERMEDIATE` 仍按现有结构推送 |

### 4.3 后端 — Multi-Agent 辩论（P1，第二阶段）

**文件**：`backend/app/multi_agent/accounting/debate_team.py`

| ID | 需求 | 说明 |
|----|------|------|
| **F-M1** | 分析师 / 质疑者 | `run_prompt_tool_loop()` 升级为真流式后自动受益 |
| **F-M2** | 裁判本轮总结 | `_judge_llm.ainvoke` 改为 `astream`，推送 `REASONING`（带 `role=judge` metadata） |
| **F-M3** | 最终裁决 | `_final_judgment` 改为流式或复用统一流式 helper |
| **F-M4** | 角色 metadata | 流式事件保留 `metadata.role` / `metadata.round` |

### 4.4 后端 — 共享流式工具函数（P0）

**新建或扩展**：`backend/app/agent/runtime.py`

| ID | 需求 | 说明 |
|----|------|------|
| **F-R1** | `stream_llm_response()` | 统一封装：`astream` + tool_call 检测 + REASONING 事件生成 |
| **F-R2** | `invoke_or_stream_llm_with_tools()` | 供 `run_react_loop` 与 `run_prompt_tool_loop` 共用 |
| **F-R3** | Provider 能力探测 | 可选：首次流式失败则 session 级标记降级（避免每轮重试） |

### 4.5 前端（P0，轻量）

**文件**：`frontend/src/stores/chat.ts`、`frontend/src/views/ChatView.vue`

| ID | 需求 | 说明 |
|----|------|------|
| **F-F1** | 保持 `reasoning`  handler | 已支持 `accumulated` / `token`，无需改协议 |
| **F-F2** | 流式光标（可选 P2） | 回答生成中显示闪烁光标 `▍` |
| **F-F3** | 滚动策略 | 流式过程中保持滚动跟随（现有 `watch messages` 已基本满足） |
| **F-F4** | 不重复渲染 FINAL | `final` 事件到达时仅关闭 `isStreaming`，避免内容闪跳 |
| **F-F5** | Markdown 增量渲染 | 维持现有 `renderMarkdown`；P2 可优化为增量解析 |

### 4.6 配置与环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGENT_STREAMING_ENABLED` | `true` | 全局开关；`false` 时全部走假流式/阻塞模式 |
| `AGENT_STREAM_FALLBACK_CHUNK_SIZE` | `24` | 降级假流式 chunk 大小（保留现有行为） |
| `AgentConfig.streaming` | `true` | 单次请求级覆盖（WebSocket 可扩展字段，本期可不改 WS 协议，读全局配置即可） |

---

## 5. 接口与事件契约

### 5.1 WebSocket 协议（不变）

客户端发送：

```json
{
  "type": "message",
  "input": "用户问题",
  "mode": "reasoning_action",
  "skill": null,
  "provider": "deepseek",
  "temperature": 0.7
}
```

服务端推送事件类型 **不变**：`start` / `thinking` / `tool_call` / `tool_result` / `reasoning` / `final` / `done` / `error`。

### 5.2 `reasoning` 事件（增强语义，向后兼容）

**真流式时（新行为）：**

```json
{
  "type": "reasoning",
  "data": {
    "token": "根据",
    "accumulated": "根据"
  },
  "metadata": {}
}
```

```json
{
  "type": "reasoning",
  "data": {
    "token": "您的",
    "accumulated": "根据您的"
  },
  "metadata": {}
}
```

**字段约定：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `token` | string | 是 | 本 chunk 新增文本（可能 1 个字符或 1 个 token） |
| `accumulated` | string | 是 | 截至当前的完整正文（前端优先使用此字段） |
| `content` | string | 否 | legacy 兼容，等价于某次 accumulated |

**频率预期：** 真流式下每轮 LLM 可能推送 **数十～数百次** `reasoning`（取决于 Provider chunk 粒度），远高于现网假流式的个位数 chunk。

### 5.3 事件时序（ReAct，无工具）

```
START → THINKING → REASONING* → FINAL → DONE
```

### 5.4 事件时序（ReAct，有工具）

```
START → THINKING → TOOL_CALL → TOOL_RESULT → THINKING → REASONING* → FINAL → DONE
```

---

## 6. 分阶段交付范围

### Phase 1 — MVP（建议首版上线）

| 模块 | 内容 |
|------|------|
| ReAct | `run_react_loop()` 真流式 + 降级 |
| 共享 helper | `stream_llm_response()` 等 |
| 配置 | `AGENT_STREAMING_ENABLED` |
| 前端 | 验证现有 handler，修复 FINAL 重复覆盖边缘 case |
| 测试 | S1、S2、S6 场景 |

**验收标准：** 推理闭环模式下，不触发工具的问题必须出现 WorkBuddy 级打字机效果。

### Phase 2 — 全模式

| 模块 | 内容 |
|------|------|
| Plan-Execute | 步骤执行 + 汇总流式 |
| Multi-Agent | 三角色 + 终审流式 |
| 测试 | S3、S4 场景 |

### Phase 3 — 体验 polish（可选）

| 模块 | 内容 |
|------|------|
| 前端 | 流式光标、Markdown 增量渲染优化 |
| 性能 | 高频 reasoning 事件节流（requestAnimationFrame 合并） |
| 观测 | TTFT / tokens-per-second 日志 |

---

## 7. 技术方案摘要

### 7.1 关键改动文件

| 文件 | 改动类型 | Phase |
|------|----------|-------|
| `backend/app/agent/runtime.py` | 核心：astream 循环、共享 helper | 1 |
| `backend/app/core/config.py` | 新增 streaming 配置项 | 1 |
| `backend/app/agent/plan_execute.py` | 间接受益 / 微调 | 2 |
| `backend/app/multi_agent/accounting/debate_team.py` | Judge/Final 流式 | 2 |
| `frontend/src/stores/chat.ts` | 边缘 case 修复 | 1 |
| `frontend/src/views/ChatView.vue` | 可选光标 | 3 |
| `docs/agent-orchestration/README.md` | 更新流式说明 | 1 |
| `REMAINING_WORK.md` | 关闭 A-4 | 1 |

### 7.2 LangChain `astream` + Tools 处理要点

1. **Chunk 聚合**：`AIMessageChunk` 需合并 `content` 与 `tool_call_chunks`。
2. **终止条件**：合并后的 message 含完整 `tool_calls` → 执行工具，**不**向用户推送 tool arguments 的正文流。
3. **空 content 工具轮**：仅展示 `TOOL_CALL` / `TOOL_RESULT` UI，用户不期望此阶段有正文。
4. **Token 统计**：流式结束后从 `response_metadata` / 最终 `AIMessage` 汇总 `tokens_used`（修复 A-2 的部分场景）。

### 7.3 Provider 兼容性

| Provider | 预期支持 | 备注 |
|----------|----------|------|
| DeepSeek（OpenAI 兼容） | ✅ | 默认 Provider，优先验证 |
| OpenAI 兼容 / Custom（Ollama、vLLM） | ✅ | 依赖 `stream=true` 实现 |
| Anthropic | ✅ | `ChatAnthropic.astream` |
| 不支持 stream 的私有化网关 | 降级 | 假流式 |

### 7.4 性能与限流

| 项 | 策略 |
|----|------|
| WS 消息频率 | 单轮回答可能 100+ 条 `reasoning`；单条 payload 小（<2KB），可接受 |
| 前端渲染 | Phase 1 直接更新；Phase 3 可选 rAF 合并 |
| 超时 | 沿用 `chat.py` 的 `asyncio.wait_for(timeout=120s)`，流式期间计时不变 |
| 背压 | FastAPI WS 发送 await；若客户端慢，依赖 OS 缓冲（本期不实现复杂背压） |

---

## 8. 非功能需求

| 类别 | 要求 |
|------|------|
| **可靠性** | 流式失败不得导致空回答；必须降级或 ERROR 事件 |
| **兼容性** | 旧版前端仅依赖 `accumulated` 字段仍可工作 |
| **安全性** | 流式内容仍经同一套 auth / session 隔离，无新泄露面 |
| **可观测性** | 降级时打 `[Streaming] fallback to simulated` 日志；可选记录 TTFT |
| **可测试性** | 提供 mock LLM 流式 chunk 的单元测试夹具 |

---

## 9. 验收标准

### 9.1 功能验收

| 编号 | 条件 | 通过标准 |
|------|------|----------|
| **AC-1** | 推理闭环 + 纯文本问答 | 发送后 **3 秒内** 聊天区出现首字符，且持续增量显示 |
| **AC-2** | 推理闭环 + 触发工具 | 先见工具卡片，工具完成后回答 **逐 token** 显示（非一次性全文） |
| **AC-3** | 任务编排汇总 | Phase 2：汇总段落逐 token 显示 |
| **AC-4** | 协同决策 | Phase 2：至少裁判总结逐 token 显示 |
| **AC-5** | 降级 | 关闭 Provider stream 或设 `AGENT_STREAMING_ENABLED=false` 时，仍完整显示回答 |
| **AC-6** | 记忆 | 流式结束后 `FINAL.output` 与聊天区最终文本一致，且写入会话记忆 |
| **AC-7** | 导出 | 流式完成后「导出」按钮内容完整 |

### 9.2 体验验收（人工）

| 编号 | 检查项 |
|------|--------|
| **UX-1** | 与 WorkBuddy / ChatGPT 对比，打字机效果无明显卡顿或「先等 10 秒再涌出」 |
| **UX-2** | 流式过程中切换路由/会话不崩溃 |
| **UX-3** | Markdown 标题、列表在流式过程中渲染不严重错乱（允许增量阶段格式不完整） |

### 9.3 回归验收

| 编号 | 检查项 |
|------|--------|
| **RG-1** | 四种 execution mode 均可完成一次完整对话 |
| **RG-2** | WebSocket 事件序列仍含 `done` |
| **RG-3** | `/health`、登录、知识库等无关模块无回归 |

---

## 10. 测试计划

### 10.1 单元测试

| 用例 | 说明 |
|------|------|
| `test_stream_llm_text_only` | mock astream 仅 content chunk → N 个 REASONING + 1 个 FINAL |
| `test_stream_llm_with_tools` | mock 先 tool_calls 后 content → 工具事件 + 正文流 |
| `test_stream_fallback_on_error` | astream 抛错 → 降级假流式，output 完整 |
| `test_streaming_disabled` | `streaming=False` → 行为与现网一致 |

### 10.2 集成测试

| 用例 | 说明 |
|------|------|
| WS 纯问答 | 连接 `/ws/chat/{session_id}`，断言 `reasoning` 事件数 > 5 |
| WS 工具问答 | 「计算 123*456」类问题，断言 `tool_call` 先于 `reasoning` |

### 10.3 手工测试清单

1. 推理闭环：「什么是 DuPont 分析？」（无工具）
2. 推理闭环：「用 calculator 算 999×888」（有工具）
3. 任务编排：「对某公司做财务审计报告」（Phase 2）
4. 协同决策：「评审某公司投资价值」（Phase 2）
5. 设置页切换 Provider 后重复 1、2

---

## 11. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| LangChain chunk 中 tool_calls 解析不完整 | 工具调用失败 | 参考 LC 官方 `AIMessageChunk` 合并工具；单测覆盖 |
| 部分 OpenAI 兼容网关 stream 格式非标准 | 特定 Provider 不可用 | 自动降级假流式 + 设置页提示 |
| 高频 reasoning 导致前端卡顿 | 长回答 UI 掉帧 | Phase 3 rAF 合并；MVP 先观察 |
| Anthropic stream + tools 行为差异 | 多 Provider 回归成本高 | MVP 以 DeepSeek 为主，Anthropic 作 Phase 2 回归 |
| FINAL 与最后 reasoning accumulated 不一致 | 导出/记忆错误 | FINAL 始终使用服务端 accumulated 权威文本 |

---

## 12. 排期建议（供评审）

| 阶段 | 工作量（估） | 交付物 |
|------|-------------|--------|
| Phase 1 MVP | 1.5–2 人日 | runtime 真流式 + 配置 + 单测 + 文档更新 |
| Phase 2 全模式 | 1 人日 | debate judge、plan 步骤验证 |
| Phase 3 Polish | 0.5–1 人日 | 光标、性能优化 |

---

## 13. 待评审决策项

请产品负责人在评审时确认：

| # | 决策项 | 建议默认 | 选项 |
|---|--------|----------|------|
| **D1** | 首版是否只做 Phase 1（ReAct） | 是 | 是 / 否，一次性 Phase 1+2 |
| **D2** | 工具调用轮是否展示「模型思考过程」流式 | 否 | 业界通常不展示 tool JSON 流 |
| **D3** | 流式失败是否对用户可见提示 | 否，静默降级 | 静默 / Toast「已切换兼容模式」 |
| **D4** | 是否在 WS 消息增加 `"streaming": true` 字段 | 否，用全局配置 | 是 / 否 |
| **D5** | Plan 阶段 JSON 是否未来流式展示 | 本期不做 | 记录为 backlog |

---

## 14. 附录

### 14.1 现网假流式代码位置

```
backend/app/agent/runtime.py
  ├── run_react_loop()           # L229–330
  ├── run_prompt_tool_loop()     # L340–393
  └── stream_text_as_reasoning() # L212–226, chunk_size=24
```

### 14.2 前端消费位置

```
frontend/src/stores/chat.ts     # ws.on('reasoning', ...)
frontend/src/views/ChatView.vue # renderMarkdown(msg.content)
```

### 14.3 参考竞品行为

WorkBuddy / ChatGPT：仅在模型输出 **自然语言回答** 时段流式；Function Call 阶段展示结构化工具 UI，不对 tool arguments 做打字机效果。本 PRD 对齐此行为。

---

## 15. 修订记录

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| 1.0 | 2026-07-29 | Agent Platform | 初稿，待评审 |

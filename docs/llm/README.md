# LLM 与配置模块

## 模块职责

LLM 模块负责**屏蔽不同大模型 Provider 的差异**，为 Agent、技能 Executor、多 Agent 角色提供统一的「创建模型 → 绑定工具 → 异步调用」能力。用户可在设置页配置 API Key、Base URL、默认模型，无需改代码即可切换 DeepSeek、OpenAI、Anthropic 或本地 Ollama。

## LLMFactory 工厂模式

### 支持的 Provider

| Provider key | 典型用途 | 底层客户端 |
|--------------|----------|------------|
| `deepseek` | 默认生产推理 | ChatOpenAI（OpenAI 兼容 API） |
| `openai` | GPT-4o 等 | ChatOpenAI |
| `anthropic` | Claude 系列 | ChatAnthropic |
| `custom` | Ollama / vLLM / OneAPI | ChatOpenAI（自定义 base_url） |

### create() 工作流程

1. 读取 `app.core.config` 中预加载的 provider 配置（来自 `.env` + `data/settings.json` 覆盖）
2. 合并运行时 override（WebSocket 消息中的 provider / model / temperature）
3. 校验 API Key 是否存在（custom 可空 key）
4. 实例化对应 LangChain ChatModel
5. 返回给 runtime 做 `bind_tools()` 与 `ainvoke()` / `astream()`

### list_providers() 与 update_provider()

- **list_providers**：返回脱敏列表（has_api_key 布尔值，不返回完整 key），供前端 SettingsView 与 Chat 模型下拉框
- **update_provider**：Settings API 调用，更新内存配置并持久化到 `data/settings.json`

## 配置加载层次

```
.env（模板 .env.example）
    │  启动时加载
    ▼
app.core.config（全局 config 对象）
    │
    ├─► apply_persisted_settings()  读取 data/settings.json 覆盖
    │
    └─► AgentConfig 运行时 override（单次请求）
```

**优先级**：单次请求 override > settings.json > .env 默认值

## 关键环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` | DeepSeek |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | OpenAI |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Anthropic |
| `CUSTOM_BASE_URL` / `CUSTOM_API_KEY` / `CUSTOM_MODEL` | 本地或第三方兼容网关 |
| `DEFAULT_LLM_PROVIDER` | 未指定时的默认 provider |

## AgentConfig 运行时参数

Agent 执行时携带的配置对象，主要字段：

- `session_id` — 关联记忆
- `provider` / `model` / `temperature` — 模型选择
- `max_iterations` — ReAct 上限
- `system_prompt` — 可选覆盖
- `persist_memory` — 是否写入记忆（Plan-Execute 子步骤为 false）

`normalize_agent_config()` 在 runtime 入口统一填充默认值。

## 与 Agent 各模式的关系

| 场景 | LLM 使用方式 |
|------|-------------|
| ReAct 主循环 | 每轮 bind_tools + ainvoke，可 astream 最终文本 |
| Plan-Execute 规划/评估 | 低温 single-shot ainvoke，期望 JSON |
| Plan-Execute 步骤执行 | 嵌套 ReAct，共享同一 provider 配置 |
| 辩论 Analyst/Skeptic | run_prompt_tool_loop，temperature 0.4/0.5 |
| 辩论 Judge | 无工具 ainvoke，temperature 0.3 |
| SkillExecutor 报告生成 | 单次 ainvoke 汇总工具结果 |

## 健康检查

`GET /health` 与 `GET /api/system/status` 会探测：

- 各 provider 是否配置了 API Key
- default_provider 是否可用

返回 `llm.status: up` 及 providers 列表，前端 App.vue 状态 pill 与 SettingsView 基础设施区展示。

## 持久化设置存储

`settings_store.py` 负责：

- 读取/写入 `data/settings.json`
- 启动时 `apply_persisted_settings()` 合并到运行时 config
- 审计日志记录 settings 变更（admin 操作）

**注意**：前端 Chat 页的 provider/model 选择会通过 WebSocket 传给后端；Settings 页的修改影响全局默认。两者是否完全一致取决于请求是否携带 override，属于已知产品层待统一项（见 PRD FR-01）。

## 代码位置

| 文件 | 职责 |
|------|------|
| `backend/app/llm/factory.py` | LLMFactory |
| `backend/app/core/config.py` | 环境变量与配置对象 |
| `backend/app/core/settings_store.py` | JSON 持久化 |
| `backend/app/api/settings.py` | REST 设置 API |

## 相关文档

- [Agent 编排](../agent-orchestration/README.md) — runtime 如何调用 LLM
- [API 与前端](../api-frontend/README.md) — Settings 页与 WS 传参

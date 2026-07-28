# 工具系统（Tools）

## 模块职责

工具系统是 Agent **与外部世界交互的桥梁**。大模型本身不能联网、不能读本地文件、不能精确算数；工具系统将这些问题封装为「模型可声明调用的函数」，在 ReAct 循环中由 runtime 实际执行并把结果回填给模型。

本平台工具设计遵循：

- **统一抽象**：所有工具继承 `BaseTool`，返回结构化 `ToolResult`
- **LangChain 互操作**：可一键转为 `StructuredTool`，供 `llm.bind_tools()` 使用
- **动态注册**：启动注册 + 运行时 register/unregister（API 可扩展）
- **分类管理**：web / general / file / accounting 等，便于技能筛选与前端过滤

## 工具生命周期

```
main.py register_all_tools()
        │
        ▼
ToolRegistry.register(tool)  ── 存储实例 + 元数据
        │
        ▼
Agent ReAct 循环
        │
        ├─► to_langchain_tools(categories?, names?)  ── 筛选子集
        │
        ├─► LLM 返回 tool_calls
        │
        └─► execute_tool_call()
                │
                ├─► registry.get(name)
                ├─► tool.execute(**args)
                └─► ToolResult.to_string() → ToolMessage
```

## BaseTool 抽象

每个工具需定义：

| 属性/方法 | 说明 |
|-----------|------|
| `name` | 唯一标识，LLM tool_call 时引用 |
| `description` | 自然语言说明，影响模型是否选择该工具 |
| `category` | 分类标签 |
| `requires_confirmation` | 是否需人工确认（预留，当前多为 false） |
| `get_parameters_schema()` | JSON Schema，定义 LLM 传入参数 |
| `execute(**kwargs)` | 实际逻辑，返回 `ToolResult(success, data, error)` |
| `to_langchain_tool()` | 转为 LangChain StructuredTool |

**ToolResult** 统一成功/失败格式，runtime 将其序列化为字符串供模型阅读。

## ToolRegistry 注册中心

全局单例能力：

- `register(tool)` / `unregister(name)` — 增删工具，重复 register 会覆盖
- `get(name)` / `get_by_category(category)` — 查询
- `list_all()` — API 返回元数据列表
- `to_langchain_tools(categories, names)` — **连接自定义工具与 LangChain Agent 的关键方法**
- `get_tool_count()` — 启动日志用

## 内置通用工具（5 个）

### web_search — 网页搜索

- **实现**：DuckDuckGo Search API（`duckduckgo-search` 库）
- **用途**：获取实时信息、新闻、公开资料
- **典型场景**：文档分析技能中补充外部背景

### calculator — 安全计算器

- **实现**：对表达式做白名单字符过滤后 `eval`（仅数字与 +-*/(). 等）
- **用途**：精确数值计算，避免 LLM 算术幻觉
- **局限**：不支持复杂函数，故意限制攻击面

### file_reader — 文件读取

- **实现**：从 `./data/` 目录读取 CSV、Excel、PDF、TXT、JSON
- **用途**：文档分析、数据可视化等技能的数据入口
- **安全**：路径限制在 data 目录，防止任意文件读取

### code_executor — Python 代码执行

- **实现**：`exec()` 执行用户/模型生成的 Python 片段，带超时
- **用途**：数据可视化占位、简单数据处理 demo
- **安全**：基础沙箱（无 import 限制完善，仅适合受信环境 demo）

### datetime — 日期时间

- **实现**：返回当前时间、日期加减等
- **用途**：审计报告时间戳、报表期别判断

## 内置会计学工具（5 个）

面向财务审计 demo，均接受 **`data` 参数（JSON 字符串）**，内含简化报表科目数值。

### balance_sheet_analyzer — 资产负债表

- **动作**：verify（验证 A=L+E）、ratio、analyze
- **输出**：勾稽是否平衡、结构占比、流动性初步判断

### income_statement_analyzer — 利润表

- **分析**：营收、毛利率、净利率、费用率等盈利指标

### cash_flow_analyzer — 现金流量表

- **分析**：经营/投资/筹资三大活动现金流结构、质量评价

### financial_ratio_calculator — 财务比率

- **维度**：盈利能力、偿债能力、营运能力、成长能力四类比率

### dupont_analysis — 杜邦分析

- **分解**：ROE = 净利率 × 资产周转率 × 权益乘数
- **用途**：定位 ROE 变动的驱动因素

**工具链协作**：财务审计技能 pipeline 按「报表验证 → 三表分析 → 比率 → 杜邦」顺序调用，最后 LLM 写报告。

## 工具与 LLM 的协作模式

ReAct 循环中，模型看到的工具列表是每个工具的 name + description + parameters schema。模型根据 description 决定是否调用、传什么参数。

**设计建议**（项目已遵循）：
- description 写清「何时该用、输入格式、输出含义」
- 会计学工具统一 JSON `data` 字段，降低模型参数编造难度
- 工具返回结构化 JSON 字符串，便于下游工具或 LLM 解析

## API

| 端点 | 说明 |
|------|------|
| `GET /api/tools` | 全部工具，可选 `?category=accounting` |
| `GET /api/tools/{tool_name}` | 单个工具详情 |

前端 ToolsView 只读浏览；ChatView 在 tool_call 事件中展示调用卡片。

## 扩展新工具

1. 继承 `BaseTool`，实现 schema 与 execute
2. 在 `main.py` 的 `register_all_tools()` 注册
3. 若需被技能使用，在技能的 `get_required_tools()` 中声明名称
4. 前端 `displayLabels.ts` 添加中文展示名（可选）

**运行时注册示例**（概念上）：`tool_registry.register(MyTool())`，无需重启即可被下一轮 ReAct 使用（当前无 REST 暴露，但 Registry 支持）。

## 安全与边界

| 工具 | 风险点 | 现状 |
|------|--------|------|
| code_executor | 任意代码执行 | 仅 demo 环境，无生产级沙箱 |
| file_reader | 路径遍历 | 限制在 data/ |
| web_search | 外部依赖 | 依赖 DuckDuckGo 可用性 |
| calculator | 代码注入 | 白名单过滤 |

## 代码位置

| 路径 | 内容 |
|------|------|
| `backend/app/tools/registry.py` | 注册中心 |
| `backend/app/tools/base.py` | 基类与 ToolResult |
| `backend/app/tools/builtin/` | 通用工具 |
| `backend/app/tools/accounting/` | 会计学工具 |
| `backend/app/api/tools.py` | REST API |

## 相关文档

- [技能模块](../skills/README.md) — 如何组合工具为业务技能
- [Agent 编排](../agent-orchestration/README.md) — ReAct 中工具调用循环
- [多 Agent 模块](../multi-agent/README.md) — 辩论角色使用的工具子集

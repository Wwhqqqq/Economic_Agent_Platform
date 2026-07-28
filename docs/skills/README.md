# 技能系统（Skills）

## 模块职责

如果说**工具（Tools）**是 Agent 的「原子能力」（计算器、读文件、搜网页），那么**技能（Skills）**就是面向业务场景的「能力套餐」。一个技能打包了：

- **专属系统 Prompt**：告诉模型以什么角色、什么流程完成任务
- **工具白名单**：只允许使用与该场景相关的工具子集
- **上下文策略**：控制记忆/RAG 加载行为（历史条数、是否查知识库等）
- **可选固定流水线**：绕过 ReAct，按预定步骤依次调工具再让 LLM 汇总

技能系统让用户（或前端 UI）通过「激活财务审计」一键切换 Agent 行为，而无需每次手写长 Prompt。

## 核心概念

### BaseSkill 技能抽象

每个技能实现统一接口：

| 方法 | 作用 |
|------|------|
| `name` / `description` / `category` / `icon` | 元数据，供 API 与前端展示 |
| `get_system_prompt()` | 注入到 Agent 系统消息最前段 |
| `get_required_tools()` | 返回工具名列表，ReAct 循环仅绑定这些工具 |
| `get_context_strategy()` | 返回 dict，如 `{ max_history, include_knowledge, ... }` |
| `execute(input, config)` | REST 直接执行入口，委托 SkillExecutor |

### SkillRegistry 技能注册中心

全局单例，职责：

- **register / unregister**：启动时注册内置技能，也支持运行时动态增删
- **activate / deactivate**：全局仅一个激活技能（进程级状态）
- **get_active**：运行时、MemoryManager、Agent runtime 查询当前技能
- **list_all**：返回含 `active` 标记的技能列表
- **_validate_tools**：激活时检查依赖工具是否已在 ToolRegistry 注册，缺失则警告但不阻断

**激活路径**：
1. WebSocket 消息携带 `skill` 字段
2. REST `POST /api/skills/{name}/activate`
3. 前端 ChatView 切换技能下拉框时调用 activate/deactivate

## 技能如何影响 Agent 执行

激活技能后，以下三处联动变化：

```
激活 skill X
    │
    ├─► resolve_system_prompt()
    │       = skill.get_system_prompt() + base prompt
    │
    ├─► get_langchain_tools()
    │       = tool_registry 按 skill.get_required_tools() 过滤
    │
    └─► MemoryManager._resolve_context_strategy()
            = skill.get_context_strategy()
```

未激活技能时，Agent 使用默认 Prompt、全部已注册工具、默认记忆策略（知识库+长期+图谱+10 条历史）。

## SkillExecutor 执行器

提供两种执行路径：

### 路径 A：固定流水线（Pipeline）

针对「步骤明确、工具调用顺序固定」的技能，直接按代码编排调用工具，最后一次性请 LLM 生成报告。**不经过 ReAct 循环**，结果确定、延迟可预期。

当前实现：

**financial_audit（财务审计）**
1. 解析用户输入中的 JSON 财务数据（或示例数据）
2. 依次调用：资产负债表分析 → 利润表 → 现金流量 → 财务比率 → 杜邦分析
3. 汇总各工具 JSON 输出
4. LLM 生成结构化审计报告（风险点、建议、结论）

**document_analysis（文档分析）**
1. 正则识别用户输入中的文件路径
2. 若有路径，调用 file_reader 读取
3. LLM 基于内容输出结构化分析报告

**data_visualization（数据可视化）**
1. 调用 code_executor 执行 matplotlib 绘图代码（占位模板）
2. LLM 解读图表含义

> **已知问题**：Executor 内 pipeline 分支判断使用了 `data_viz` 而非注册名 `data_visualization`，导致数据可视化技能实际总是 fallback 到 ReAct 路径。

### 路径 B：ReAct 回退（run_via_react）

若技能无专属 pipeline 或 pipeline 未命中，Executor 临时激活技能 → 调用 `collect_react_response()` → 返回完整 Agent 响应。

REST `POST /api/skills/{name}/execute` 与 SkillsView 的「试运行」走此路径。

## 内置技能一览

| 技能名 | 中文场景 | 分类 | 依赖工具 | 执行方式 |
|--------|----------|------|----------|----------|
| `financial_audit` | 财务审计 | accounting | 5 个会计学工具 + calculator | Pipeline |
| `document_analysis` | 文档分析 | document | file_reader, calculator, code_executor, web_search | Pipeline |
| `data_visualization` | 数据可视化 | data | file_reader, code_executor, calculator | 预期 Pipeline，实际多走 ReAct |

### financial_audit 深度说明

面向答辩/demo 的核心技能。Prompt 要求模型以审计师视角，工具链覆盖：

- 报表勾稽（资产 = 负债 + 权益）
- 盈利能力、偿债能力、营运能力比率
- 杜邦 ROE 分解
- 现金流质量

用户可在 Chat 页选择该技能后粘贴 JSON 格式简化报表数据，Agent 会自动走审计流水线。

### document_analysis 深度说明

强调从 `./data/` 目录读取本地文件（CSV、Excel、PDF、TXT、JSON）。适合演示「上传制度文件 → 激活文档分析 → 提问摘要」链路。

### data_visualization 深度说明

设计意图是 code_executor 生成图表 + LLM 解读。因命名不一致，建议 demo 时优先通过 Chat + 技能激活走 ReAct，或修复 Executor 分支条件。

## context_strategy 示例

技能可定制记忆行为，例如财务审计可能配置：

- `max_history: 15` — 保留更多对话上下文以对比多期数据
- `include_knowledge: true` — 检索会计准则知识库
- `include_entities: true` — 启用图谱关联
- `include_long_term: true` — 召回历史审计讨论

DocumentAnalysis 可能关闭 web 无关记忆以聚焦文件内容。

## API 一览

| 端点 | 说明 |
|------|------|
| `GET /api/skills` | 列表（含 active、required_tools、context_strategy） |
| `POST /api/skills/{name}/activate` | 激活 |
| `POST /api/skills/deactivate` | 取消激活 |
| `POST /api/skills/{name}/execute` | 同步执行（body: `{ input, provider?, model? }`） |

## 与 Tools 模块的关系

技能**不实现**工具逻辑，仅**声明依赖**。**ToolRegistry 必须先于 SkillRegistry 完成注册**（main.py 中先 tools 后 skills）。

激活时 `_validate_tools` 确保依赖存在；缺失工具会打印 Warning，技能仍会激活，但 ReAct 可能因工具不可用而失败。

## 扩展新技能

1. 继承 `BaseSkill`，实现 prompt / tools / strategy / execute
2. 在 `main.py` 的 `register_all_skills()` 中注册
3. （可选）在 `SkillExecutor` 中添加 pipeline 函数
4. 前端 `displayLabels.ts` 补充展示名称（可选）

## 设计权衡

- **全局单激活**：实现简单，但不适合多用户并发不同技能；生产环境应改为 session 级技能状态。
- **Pipeline vs ReAct**：Pipeline 可控但僵化；ReAct 灵活但结果不确定。财务审计选 Pipeline 是为了 demo 稳定性。
- **WorkBuddy 风格**：技能 = Prompt 模板 + 工具组合 + 上下文策略，与 Cursor Skills 产品思路类似。

## 代码位置

| 文件 | 职责 |
|------|------|
| `backend/app/skills/registry.py` | 注册中心 |
| `backend/app/skills/base.py` | 抽象基类 |
| `backend/app/skills/executor.py` | Pipeline 与 ReAct 执行 |
| `backend/app/skills/builtin/*.py` | 三个内置技能 |
| `backend/app/api/skills.py` | REST API |

## 相关文档

- [工具模块](../tools/README.md) — 技能依赖的原子能力
- [Agent 编排](../agent-orchestration/README.md) — 聊天链路如何消费激活技能
- [记忆模块](../memory/README.md) — context_strategy 详解

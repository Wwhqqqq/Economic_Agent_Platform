# 多 Agent 协同模块

## 模块职责

多 Agent 模块解决**单一 Agent 难以覆盖「观点冲突、交叉验证、集体裁决」**类任务。与 ReAct「一个大脑调工具」不同，这里模拟**多个角色各自推理、互相质疑、最终合议**的人类专家会议流程。

本平台当前生产实现为 **会计学财务评审委员会（AccountingDebateTeam）**，在「协同决策（collaborative_decision）」执行模式下由 AgentOrchestrator 实例化并调度。

## 设计模式

### MultiAgentTeam 抽象

`team.py` 定义多 Agent 团队基类，约定 `invoke()` / `stream()` 接口，与 ReAct、Plan-Execute 同级，均可被编排器统一调度。

### DebateOrchestrator 辩论框架

`debate.py` 提供通用辩论数据结构：

- **DebateRound**：单轮记录，含 proposer（正方）与 opponent（反方）论点
- **DebateResult**：完整辩论结果，含各轮摘要与最终裁决

AccountingDebateTeam 在此基础上实现三轮角色与多轮循环。

## 财务评审委员会：三角色模型

| 角色 | 代号 | 温度 | 是否用工具 | 职责 |
|------|------|------|-----------|------|
| 财务分析师 | Analyst / Proposer | 0.4 | 是 | 正方：基于数据分析给出投资/审计结论 |
| 审计质疑官 | Skeptic / Opponent | 0.5 | 是 | 反方：挑战假设、找红旗、提替代解释 |
| 首席裁决官 | Judge | 0.3 | 否 | 中立：综合各方论点，输出最终裁决 |

**工具范围**：分析师与质疑官共享 accounting + general + web 三类工具（资产负债表、比率、杜邦、计算器、搜索等），可在辩论中用数据验证对方观点。

**裁决官不用工具**：仅基于文本论点做 meta-reasoning，避免「用工具再算一遍」削弱辩论张力。

## 单轮辩论流程

每一轮（round）按固定顺序执行：

```
Round N
   │
   ├─► ① Analyst
   │      输入：辩题 + 前轮上下文 + 角色系统 Prompt
   │      执行：run_prompt_tool_loop（最多 5 次工具迭代）
   │      输出：分析师论点 + tool_calls 记录
   │
   ├─► ② Skeptic
   │      输入：辩题 + 前轮上下文 + 分析师本轮论点
   │      执行：同上，带工具
   │      输出：质疑官反驳 + tool_calls
   │
   └─► ③ Judge（本轮小结）
          输入：分析师 + 质疑官本轮论点
          执行：纯 LLM 调用（无工具）
          输出：本轮共识与分歧摘要
```

**前轮上下文**：上一轮分析师/质疑官/裁决摘要拼接，使辩论逐轮深入而非重复。

**最大轮数**：由 `DEBATE_MAX_ROUNDS` 控制，默认 3。轮数越多，论点越充分，但 token 成本与延迟线性增长。

## 最终裁决

所有轮次结束后，Judge 收到**完整辩论历史**，生成 Markdown 结构终稿，通常包含：

- **Verdict（裁决结论）**：买/卖/持有、通过/否决议等（依辩题而定）
- **Key Findings（关键发现）**
- **Risks（风险点）**
- **Consensus（共识区）**
- **Next Steps（后续建议）**

该终稿作为 `FINAL` 事件输出，并写入 `MemoryManager.save_context()`，供后续会话召回。

## 流式事件与前端展示

辩论模式复用 Agent 事件体系，额外在 `metadata` 中标注：

- `role`: `analyst` / `skeptic` / `judge`
- `round`: 当前轮次编号

前端 ChatView 可根据 metadata 分栏或分色展示「正方 / 反方 / 裁判」内容，形成辩论时间线。

典型事件序列：

```
START → THINKING/TOOL_CALL/REASONING（分析师）→ ... →（质疑官）→ ... →（裁判小结）
→ 重复至 max_rounds → FINAL（总裁决）→ DONE
```

## 与编排器的集成

```
用户选择 collaborative_decision 或 adaptive + 关键词「辩论/评审/委员会」
        │
        ▼
AgentOrchestrator._get_agent("collaborative_decision")
        │
        ▼
new AccountingDebateTeam()   ← 每请求新建，无跨请求状态
        │
        ▼
team.stream(user_input, config)
```

**辩题来源**：用户输入整段作为 debate topic，可包含 JSON 财务数据或公司名称+问题描述。

## Prompt 工程要点

各角色 System Prompt 在 `debate_team.py` 中硬编码（英文），强调：

- **Analyst**：先验证报表勾稽，再算比率/杜邦，结论需有数字支撑
- **Skeptic**： forensic accounting 视角，质疑 aggressive accounting
- **Judge**： 25 年资本市场经验，平衡双方，明确剩余分歧

生产环境可将 Prompt 外置为配置或技能化。

## 共享运行时

辩论角色不重复实现 ReAct，而是调用 `runtime.run_prompt_tool_loop()` 与 `collect_prompt_tool_response()`：

- 传入独立 HumanMessage prompt（含角色指令 + 辩题 + 上下文）
- 绑定 `_debate_tools` 子集
- `ROLE_MAX_TOOL_ITERATIONS = 5`，低于主 ReAct 的 10，控制单角色耗时

Judge 使用 `create_llm(temperature=0.3).ainvoke()` 单次调用。

## 适用场景与局限

**适合**：
- 投资决策评审 demo
- 财务数据质量争议
- 答辩展示「多 Agent 不等于多工具，而是多视角推理」

**局限**：
- 仅实现会计领域一套角色，扩展需新建 Team 类
- 角色 Prompt 固定英文，与中文 UI 混用
- 无「用户介入辩论」机制，纯自动化
- 与 LangChain Multi-Agent 官方 AgentExecutor 不同，是自研轻量编排

## 配置项

| 环境变量 | 默认值 | 作用 |
|----------|--------|------|
| `DEBATE_MAX_ROUNDS` | 3 | 辩论轮数上限 |

## 代码位置

| 文件 | 职责 |
|------|------|
| `backend/app/multi_agent/accounting/debate_team.py` | 财务评审委员会实现 |
| `backend/app/multi_agent/debate.py` | 辩论轮次数据结构 |
| `backend/app/multi_agent/team.py` | 团队抽象基类 |

## 演示话术建议

1. 输入：「请对以下 JSON 财务数据开展三轮投资辩论：{...}」
2. 模式选「协同决策」
3. 观察分析师先调 balance_sheet / ratio 工具
4. 质疑官指出现金流与利润背离等红旗
5. 裁判给出带章节结构的最终 Markdown 裁决

## 相关文档

- [Agent 编排](../agent-orchestration/README.md) — 模式路由与事件模型
- [工具模块](../tools/README.md) — 辩论中可用的会计学工具
- [技能模块](../skills/README.md) — 技能与多 Agent 互斥（一次一种增强模式）

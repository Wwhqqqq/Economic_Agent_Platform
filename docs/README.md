# Agent Platform 项目文档

本目录按**功能模块**组织项目说明，面向需要整体理解系统设计与实现逻辑的读者。各模块文档以自然语言为主，侧重「做什么、为什么、怎么串起来」，而非逐行代码解读。

## 文档结构

| 模块 | 路径 | 说明 |
|------|------|------|
| 系统总览 | [system-overview/](./system-overview/) | 整体架构、请求链路、模块关系 |
| Agent 编排 | [agent-orchestration/](./agent-orchestration/) | 执行模式、ReAct、Plan-Execute、运行时引擎 |
| 记忆系统 | [memory/](./memory/) | 短期 / 长期 / 情景三层记忆 |
| RAG 检索 | [rag/](./rag/) | 向量库、知识图谱、混合检索与入库 |
| 技能系统 | [skills/](./skills/) | 技能注册、激活、内置技能与执行流水线 |
| 工具系统 | [tools/](./tools/) | 工具注册、通用工具、会计学工具 |
| 多 Agent 协同 | [multi-agent/](./multi-agent/) | 辩论团队、角色分工、多轮决策 |
| LLM 与配置 | [llm/](./llm/) | 多 Provider 工厂、运行时配置 |
| API 与前端 | [api-frontend/](./api-frontend/) | REST / WebSocket、页面与状态管理 |
| **多用户体系（设计）** | [多用户/](./多用户/) | MySQL 多租户、登录鉴权、记忆/RAG 隔离、安全与实施路线 |

## 与其他文档的关系

- `defense/`：答辩演示向的精简版技术说明，与本目录内容互补。
- `PRD-v2-business-completion.md`：产品待完善项与业务缺口清单。
- `多用户/`：多用户 + MySQL 完整设计方案（仅设计，不含实现代码）。

## 技术栈速览

- **后端**：FastAPI + LangChain（ReAct 工具循环）+ ChromaDB + Neo4j
- **前端**：Vue 3 + Pinia + Element Plus + Vite
- **基础设施**：Docker 运行 ChromaDB（:8001）与 Neo4j（:7474 / :7688）

## 建议阅读顺序

1. [系统总览](./system-overview/README.md) — 建立全局地图  
2. [Agent 编排](./agent-orchestration/README.md) — 理解核心执行链路  
3. [记忆](./memory/README.md) + [RAG](./rag/README.md) — 理解上下文如何被组装  
4. [工具](./tools/README.md) + [技能](./skills/README.md) — 理解能力如何被扩展  
5. [多 Agent](./multi-agent/README.md) — 理解协同决策场景  
6. [API 与前端](./api-frontend/README.md) — 理解用户如何触达上述能力  

# Agent Platform — 智能体平台

面向面试展示的全栈智能体平台，完美实践 LangChain + LangGraph + 多Agent协同。

## 克隆与部署

```bash
git clone https://github.com/Wwhqqqq/Economic_Agent_Platform.git
cd Economic_Agent_Platform
```

### 环境要求

| 软件 | 用途 |
|------|------|
| Docker Desktop | ChromaDB + Neo4j |
| Python 3.10+ | 后端 |
| Node.js 18+ | 前端 |

### 首次配置

1. 复制环境变量模板并填入 API Key（**`.env` 不在仓库中，需自行配置**）：

```bash
cp .env.example .env
# 编辑 .env，至少填入 DEEPSEEK_API_KEY 或其他 LLM Provider 的 Key
```

2. 启动 Docker 数据库、后端、前端（见下方「快速启动」）。

> **数据说明**：知识库向量数据（ChromaDB）和知识图谱（Neo4j）在首次 `docker-compose up -d` 后写入 `data/docker/`。若需迁移已有数据，将整个 `data/` 目录拷贝到新机器即可。

## 快速启动

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 OpenAI API Key 或其他 Provider 的配置
```

### 2. 启动基础设施（Docker）

```bash
docker-compose up -d
```

这将启动：
- **ChromaDB** :8001（向量数据库）
- **Neo4j** :7474 / :7687（知识图谱）

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

或使用启动脚本：

```bash
# Windows
start.bat

# Linux/Mac
bash start.sh
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

## 项目亮点

| 特性 | 实现 | 技术 |
|------|------|------|
| Agent引擎 | ReAct + Plan-Execute 双模式 | LangGraph StateGraph |
| 多Agent协同 | 会计学辩论团队（分析师/质疑者/裁判） | LangChain Multi-Agent |
| 工具系统 | 10+ 内置工具，动态注册/卸载 | Runnable 表达式 |
| 技能系统 | 工具组合 + Prompt模板 + 上下文策略 | WorkBuddy 风格 |
| 三层记忆 | 短期(会话) + 长期(向量) + 情景(图谱) | ChromaDB + Neo4j |
| 混合检索 | 向量语义 + 图谱结构 RRF 融合 | RRF 算法 |
| 多Provider | OpenAI / Anthropic / 本地兼容 | LLMFactory |
| 流式输出 | WebSocket token 级实时推送 | FastAPI WebSocket |
| LCEL集成 | 全链路 Runnable 链式编排 | LangChain LCEL |
| 知识图谱 | 实体关系存储与图检索 | Neo4j Cypher |

## API 概览

| 端点 | 说明 |
|------|------|
| `WS /ws/chat/{session_id}` | WebSocket 实时聊天 |
| `GET /api/tools` | 获取所有工具 |
| `GET /api/skills` | 获取所有技能 |
| `POST /api/skills/{name}/activate` | 激活技能 |
| `GET /api/agents` | 获取 Agent 列表 |
| `GET /api/agents/models` | 获取可用模型 |
| `POST /api/knowledge/upload` | 上传知识文档 |
| `POST /api/knowledge/search` | 知识库检索 |
| `GET /api/settings/llm` | 获取 LLM 配置 |
| `PUT /api/settings/llm` | 更新 LLM 配置 |

## 面试演示路径

1. **展示工具系统**：打开 Tools 页面，展示 10 个工具的自动注册
2. **演示财务审计**：选择 Financial Audit 技能，输入示例财务数据
3. **多Agent辩论**：切换到 Multi-Agent 模式，触发会计学三Agent辩论
4. **知识图谱**：上传文档，演示向量检索+图谱检索
5. **设置页面**：绑定自定义 URL 和 API-Key，切换模型
6. **RAG演示**：上传会计学文档，搜索相关知识

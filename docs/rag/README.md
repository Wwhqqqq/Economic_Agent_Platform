# RAG 检索增强模块

## 模块职责

RAG（Retrieval-Augmented Generation，检索增强生成）模块负责**企业知识资产的管理与检索**，让 Agent 在回答问题时能够引用用户上传的文档，而不是仅依赖模型参数记忆。

本平台 RAG 的特色是**双通道检索 + RRF 融合**：

- **向量通道**：基于 ChromaDB 的语义相似度，擅长「意思相近但措辞不同」的匹配
- **图谱通道**：基于 Neo4j 的实体、文档、关系查询，擅长「同一公司/指标在不同文档中的关联」

两路结果通过 RRF（Reciprocal Rank Fusion，倒数排名融合）算法合并排序，兼顾语义与结构。

## 模块组成

### 1. VectorStoreRetriever（向量检索）

**存储**：ChromaDB 集合 `knowledge_base`（与长期记忆的 `long_term_memory` 集合分离）。

**能力**：
- 文档增删改查
- 按 query 语义检索 top-K
- 返回 LangChain `Document` 对象，metadata 含 `doc_id`、`score`、`source=vector`

**Embedding**：使用 Chroma 内置 embedding 函数（远程模式下由 Chroma 服务处理）。

### 2. KnowledgeGraphRetriever（图谱检索）

**存储**：Neo4j 中的 `Document`、`Entity` 节点及关系边。

**检索策略**：
- 用关键词正则匹配 Document 节点标题/摘要
- 查找名称匹配的 Entity 节点
- 扩展 Entity 的一跳关系（`RELATED_TO`、`MENTIONS` 等）
- 将匹配结果封装为 `Document`，metadata 含 `entity_name`、`source=knowledge_graph`

**降级**：Neo4j 不可用时返回空列表，不阻塞向量检索。

### 3. HybridRetriever（混合检索器）

对外主入口，支持三种模式：

| 模式 | 行为 |
|------|------|
| `vector` | 仅向量检索 |
| `graph` | 仅图谱检索 |
| `hybrid` | 双路检索 + RRF 融合（默认） |

**RRF 融合算法**（简化理解）：

对两路排名列表中的每个文档，按其排名 r 累加得分 `1 / (k + r)`，其中 k 默认 60。同一文档在两路都出现则得分叠加，最终按总分降序取 top-K。

**优势**：不需要统一不同检索器的原始分数尺度，工程上稳定可靠。

**日志**：融合后会打印「向量 N 条 + 图谱 M 条 → 结果 K 条」，便于调试。

### 4. EntityExtractor（实体提取）

**定位**：知识**入库**与**情景记忆**共用的规则式实体抽取器（非 LLM）。

**规则示例**：
- 财务领域关键词：资产负债表、ROE、现金流等
- 中文公司名模式：`XX公司`、`XX集团`
- 中英文专有名词 token

**输出**：`[{ name, type, properties }]`，供 Neo4j 建节点。

**局限**：无法理解复杂指代（如「该公司」指向谁），适合结构化/半结构化文档演示。

## 知识入库流程（add_knowledge）

用户通过 API 或前端上传文本/文件时，HybridRetriever 协调以下步骤：

```
原始文本
   │
   ├─► 写入 Chroma vector store（分块 + embedding）
   │
   ├─► extract_entities() 提取实体
   │
   ├─► Neo4j 创建 Document 节点
   │
   ├─► 创建 Entity 节点，Document -[MENTIONS]-> Entity
   │
   └─► 共现 Entity 之间建立 RELATED_TO 边
```

**文档标题**：由 `build_document_title()` 从内容首行或文件名生成，便于图谱展示。

**文件上传支持**：`.txt`、`.md`、`.csv`、`.json` 等，后端读取文本内容后走同一入库管线。

## 检索在系统中的调用点

### 对话时自动检索

`MemoryManager.load_context_bundle()` 在用户提问长度 > 2 时，以 `hybrid` 模式检索 top-K，结果写入系统 Prompt 的「Retrieved Knowledge Base」段落，并生成 citations 供前端展示。

### 知识库页面手动检索

前端 KnowledgeView 调用 `POST /api/knowledge/search`，可切换 `hybrid / vector / graph` 模式，用于运维验证与 demo 演示。

### 统计与列表

- `GET /api/knowledge/stats`：文档数、实体数等
- `GET /api/knowledge/documents`：文档列表
- `DELETE /api/knowledge/{doc_id}`：删除向量与图谱中的对应数据

## API 与权限

| 端点 | 说明 | 认证 |
|------|------|------|
| `POST /api/knowledge/upload` | 文本上传 | 需登录（AUTH_ENABLED 时） |
| `POST /api/knowledge/upload/file` | 文件上传 | 需登录 |
| `POST /api/knowledge/search` | 检索 | 公开 |
| `GET /api/knowledge/documents` | 列表 | 公开 |
| `DELETE /api/knowledge/{doc_id}` | 删除 | 需登录 |

上传/删除操作会写入审计日志。

## 基础设施依赖

| 组件 | 默认地址 | Docker 服务 |
|------|----------|-------------|
| ChromaDB | localhost:8001 | `chromadb/chroma:0.5.20` |
| Neo4j Browser | localhost:7474 | `neo4j:5.25.1-community` |
| Neo4j Bolt | localhost:7688 | 映射容器 7687 |

**持久化目录**：`data/docker/chroma`、`data/docker/neo4j`，`docker-compose up -d` 后数据保留在宿主机。

**Chroma 连接模式**：
- 优先 HTTP 连接远程服务（Docker）
- 失败则 fallback 本地 PersistentClient（`data/chroma/`）

## 配置项

| 环境变量 | 作用 |
|----------|------|
| `CHROMA_HOST` / `CHROMA_PORT` | 远程 Chroma 地址 |
| `CHROMA_PERSIST_DIR` | 本地 fallback 路径 |
| `CHROMA_CONNECT_TIMEOUT` | 连接超时 |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | 图谱连接 |
| `NEO4J_DATABASE` | 数据库名 |

## 代码位置

| 文件 | 职责 |
|------|------|
| `backend/app/rag/hybrid.py` | 混合检索与 RRF |
| `backend/app/rag/vector_store.py` | Chroma 向量 CRUD |
| `backend/app/rag/knowledge_graph.py` | Neo4j 图谱检索 |
| `backend/app/rag/entity_extractor.py` | 规则实体提取 |
| `backend/app/rag/service.py` | 单例 accessor |
| `backend/app/api/knowledge.py` | REST API |

## 演示建议

1. 上传一份会计学制度 PDF/文本 → 观察实体提取结果
2. 在知识库页分别用 vector / graph / hybrid 搜索同一关键词，对比结果差异
3. 在聊天中提问文档相关内容 → 查看 citation 卡片是否正确引用

## 相关文档

- [记忆模块](../memory/README.md) — RAG 结果如何注入对话上下文
- [系统总览](../system-overview/README.md) — 数据存储分布

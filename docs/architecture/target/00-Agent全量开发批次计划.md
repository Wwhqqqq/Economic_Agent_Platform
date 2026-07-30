# Agent 全量开发批次计划

> **版本**：1.0  
> **日期**：2026-07-31  
> **作者角色**：替代人工、由 Agent 全栈完成 Target 01–05 全部实现  
> **配套设计**：[01 PDF](./01-PDF知识资产入库与预处理.md) · [02 向量图谱](./02-向量库与知识图谱分工与存储.md) · [03 专家](./03-专家中心运行时架构.md) · [04 技能](./04-技能包导入与运行时.md) · [05 媒体](./05-媒体资产与多模态解析.md)

---

## 0. 我会怎么分？

若由我**从头实现 Target 全部内容**，我会分成 **5 个批次**，不做「空壳地基批」单独交付——**每一批结束都有可演示的用户价值**。

| 批次 | 名称 | 我估工作量 | 交付后用户能做什么 |
|:----:|------|:----------:|-------------------|
| **1** | 分块 RAG 地基 | 大 | 长文档分块上传、按段落检索、引用溯源 |
| **2** | 专家与技能配置化 | 中 | YAML 扩专家/技能、Summon API、无全局 skill 污染 |
| **3** | PDF 文本层 + 图片 OCR | 大 | 上传 PDF（可复制文本）和图片截图进知识库 |
| **4** | 表格 / 扫描 / 智能检索 / Pipeline | 大 | 财报 PDF 表格问答、fact 精确查数、审计 pipeline |
| **5** | VLM 图表 + 聊天读图 | 中 | PDF 内图表理解、聊天框拖图问答 |

**不做进 5 批的内容**（除非你后续点名）：CLIP 以图搜图、技能 ZIP 市场、Office docx、MinerU 全页引擎、企业后台 CRUD 专家。

**依赖顺序**：`1 → 2` 与 `1 → 3 → 4 → 5`；批次 2 可在批次 1 完成后与批次 3 **并行**，但我默认 **串行 1→2→3→4→5** 风险最低。

---

## 1. 现状起点（我接手时）

| 模块 | 现状 | 批次 1 要动 |
|------|------|-------------|
| 知识上传 | 整篇 UTF-8，`chunk_count=1` | 重写 |
| Chroma | 存全文 embedding | 改 chunk_id |
| Neo4j | Document + Entity 规则抽取 | 保留，改锚点 |
| 专家中心 | Python dict + 前端 MVP | 批次 2 YAML 化 |
| 斜杠技能 | Python 类注册 | 批次 2 SKILL.md |
| PDF/图片 | 不支持 | 批次 3 起 |
| 异步 Job | 无 | 批次 1 引入 |
| 对象存储 | 本地 `data/uploads` | 批次 1 抽象层 |

---

## 2. Batch 1 — 分块 RAG 地基

**目标**：文本知识库从「整篇糊进去」变成「chunk 主存 + 向量索引 + 图谱双写」，全文只存一份。

### 2.1 我要新建的文件

```
backend/
  alembic/versions/003_knowledge_chunks_jobs.py
  app/
    storage/
      __init__.py
      local.py              # LocalStorage（先本地，接口兼容 S3）
      base.py               # StorageBackend 协议
    jobs/
      __init__.py
      broker.py             # ARQ 或 Celery 配置
      tasks.py              # parse_document_task
      status.py             # JobStatus enum + Redis/MySQL 持久化
    ingestion/
      __init__.py
      ndm.py                # NormalizedDocumentModel dataclass
      chunker.py            # 结构感知分块（标题/段落/ overlap）
      text_pipeline.py      # 纯文本 ingest 主入口
    rag/
      index_router.py       # IndexRouter.route(chunk) → vector/graph
      chunk_store.py        # MySQL chunk CRUD
    db/models/
      knowledge_chunk.py
      ingest_job.py
```

### 2.2 我要修改的文件

| 文件 | 改动 |
|------|------|
| `app/db/models/knowledge.py` | 增加 `parse_status`, `parser_version`, `quality_score`, `ndm_uri`, `page_count` |
| `app/services/knowledge_service.py` | `upload_text` → 触发异步 Job，不再同步写 Chroma |
| `app/rag/hybrid.py` | `add_knowledge` 改为接收 chunk 列表；`retrieve` 回查 chunk_store |
| `app/rag/vector_store.py` | id=chunk_id；document 字段仅 preview 200 字 |
| `app/rag/knowledge_graph.py` | Document 节点增加 chunk 引用；snippet 截断 200 字 |
| `app/api/knowledge.py` | 返回 `{doc_id, status}`；新增 `GET /documents/{id}/status` |
| `app/memory/manager.py` | 检索结果 citation 带 chunk_id、section_path |
| `frontend/src/views/KnowledgeView.vue` | 解析状态、chunk_count、上传进度 |
| `frontend/src/api/client.ts` | `fetchDocStatus`, citation 字段 |
| `docker-compose.yml` | Redis（若未有）供 Job 队列 |

### 2.3 实现顺序（我实际写代码的顺序）

1. Migration + `KnowledgeChunk` / `IngestJob` 模型  
2. `LocalStorage` + 原文件路径规范 `data/objects/{user_id}/{doc_id}/`  
3. `chunker.py`：Markdown 按 `#` 标题切；plain text 按空行+token 上限切  
4. `text_pipeline.py`：paste/file → NDM → chunks → MySQL  
5. `index_router.py`：每个 chunk → vector + graph（复用 `extract_entities`）  
6. ARQ task：`run_text_ingest(doc_id)`  
7. 改 `knowledge_service.upload_text` 为「建 doc 记录 → enqueue job」  
8. 改 `HybridRetriever.retrieve`：vector 命中 → `chunk_store.get_text(chunk_id)`  
9. 前端状态轮询 + 列表展示 chunk_count  
10. 删除文档：级联删 chunks + Chroma ids + Neo4j doc  

### 2.4 本批完成标准（我自检）

- [ ] 上传 8000 字 Markdown，`chunk_count >= 5`  
- [ ] 搜索命中中间章节，citation 含 section 标题  
- [ ] 删文档后 Chroma/Neo4j 无残留  
- [ ] 上传接口 < 500ms 返回（解析在后台）  
- [ ] 旧 `.txt` 上传路径仍可用  

### 2.5 本批不做

PDF、图片、Query Router、fact 表、SKILL.md

---

## 3. Batch 2 — 专家与技能配置化

**目标**：专家/技能从 Python 硬编码变为 YAML/SKILL.md；Summon 前后端一致；去掉全局 `active_skill`。

### 3.1 我要新建的文件

```
backend/
  experts/
    finance_reviewer.yaml
    report_analyst.yaml
    document_insight.yaml
    finance_review_board.yaml
  experts/_policies/
    tool_policies/accounting_full.yaml
    memory_policies/heavy_knowledge.yaml
  app/
    core/
      expert_loader.py          # YAML → expert_catalog 兼容层
      runtime_policy.py         # resolve(session, message) 优先级
    api/
      session_context.py        # POST/DELETE summon, skill
  skills/
    financial_audit/
      SKILL.md
      prompts/system.md
      policies/tools.yaml
      policies/context.yaml
    document_analysis/
      SKILL.md
      ...
    data_visualization/
      SKILL.md
      ...

frontend/
  （改动为主，少新建）
```

### 3.2 我要修改的文件

| 文件 | 改动 |
|------|------|
| `app/core/expert_catalog.py` | 改为从 `expert_loader` 读 YAML；保留 `resolve_expert_context` |
| `app/skills/registry.py` | 从 skillpack 目录加载；DB 表 `skill_installations` |
| `app/agent/runtime.py` | 仅用 `AgentConfig.active_skill`，不读全局 active |
| `app/api/chat.py` | 调 `runtime_policy.resolve`；`clear_expert`/`clear_skill` 处理 |
| `app/core/session_context.py` | 可选持久 Redis |
| `main.py` | `register_all_skills` 改为扫描 `skills/` 目录 |
| `frontend/.../ChatView.vue` | clear chip 调 API |
| `frontend/stores/settings.ts` | summon 后调 backend sync |

### 3.3 实现顺序

1. 定义 SKILL.md schema + 解析器（PyYAML front matter）  
2. 把 3 个 builtin skill 迁到 `skills/*/SKILL.md`  
3. Registry 启动扫描；`/api/skills/invocable` 读 DB+filesystem  
4. 写 4 个 expert YAML + `expert_loader.py`  
5. `runtime_policy.py`：实现 03 文档优先级表  
6. `POST /api/sessions/{id}/summon`、`DELETE .../summon`  
7. 前端 chip 清除调 API  
8. 删除 `skill_registry._active_skill` 在 chat 路径的使用  
9. 并发测试：两 session 不同 skill  

### 3.4 本批完成标准

- [ ] 新增 skill = 新建 `skills/foo/SKILL.md` + 重启，不出现在 `main.py`  
- [ ] 新增 expert = 新建 `experts/foo.yaml`  
- [ ] 召唤专家 → 刷新页面 → chip 仍在  
- [ ] `/financial_audit` 覆盖专家 default skill  
- [ ] 10 并发 session skill 不串  

### 3.5 本批不做

Team Protocol YAML 引擎、Pipeline YAML、ZIP 安装

---

## 4. Batch 3 — PDF 文本层 + 图片 OCR

**目标**：知识库支持 PDF（有文本层）和 PNG/JPG；页眉页脚去掉；扫描 PDF 标记待处理。

### 4.1 我要新建的文件

```
backend/
  app/
    ingestion/
      pdf/
        __init__.py
        classifier.py         # native_text / scanned / table_heavy
        extractor.py          # PyMuPDF 文本+ bbox
        preprocessor.py       # 页眉页脚/重复块/空白
      media/
        __init__.py
        service.py            # MediaAssetService
        ocr.py                # PaddleOCR 封装
        classifier.py         # document_scan / chart / ...
    db/models/media_asset.py
  alembic/versions/004_media_assets_pdf_fields.py
```

### 4.2 我要修改的文件

| 文件 | 改动 |
|------|------|
| `ingestion/text_pipeline.py` | 抽象公共「NDM → chunk → index」 |
| `ingestion/pdf/` | 新 pipeline 挂到 Job task |
| `jobs/tasks.py` | `run_pdf_ingest`, `run_media_ingest` |
| `app/api/knowledge.py` | `accept pdf`；`POST /upload/media` |
| `app/tools/builtin/file_reader.py` | 与 media 存储路径对齐（可选） |
| `frontend/KnowledgeView.vue` | accept `.pdf,.png,.jpg,.webp`；进度条 |
| `requirements.txt` | pymupdf, paddleocr（或 docker 化 OCR 服务） |

### 4.3 实现顺序

1. `media_assets` 表 + `MediaAssetService.upload`  
2. OCR 封装：单图 → `ocr_text` + quality  
3. 图片 ingest：OCR text → NDM figure block → figure_summary chunk → index  
4. PDF classifier：有/无 text layer  
5. PyMuPDF 抽文本 + block bbox  
6. `preprocessor.py`：跨页重复块检测 → 标记 header/footer 丢弃  
7. PDF native 路径 → NDM（带 page/block）→ 复用 batch1 chunker（按页/节）  
8. scanned PDF：`parse_status=needs_review`，不写乱码  
9. 前端上传 PDF + 图片 + Job 状态  
10. 集成测试：10 页带重复页眉 PDF + 截图 PNG  

### 4.4 本批完成标准

- [ ] 可复制 PDF 入库检索正确  
- [ ] 页眉文字不在 top-3 检索结果  
- [ ] PNG 截图 OCR 文字可问答  
- [ ] 扫描 PDF 状态 `needs_review`，不污染索引  
- [ ] 128 页 PDF 异步完成，UI 不阻塞  

### 4.5 本批不做

表格结构化、VLM、扫描 OCR 全量、聊天 vision

---

## 5. Batch 4 — 表格 / 扫描 OCR / Fact / 智能检索 / Pipeline

**目标**：财报类 PDF 可用；数值精确查；检索变聪明；专家团与财务 skill 配置化执行。

### 5.1 我要新建的文件

```
backend/
  app/
    ingestion/pdf/
      table_extractor.py      # pdfplumber + table → cells JSON
      table_chunker.py        # summary + row chunks
      ocr_pipeline.py         # 扫描页渲染+OCR
      financial_template.py   # 三表章节识别（可选）
    rag/
      query_router.py         # intent → vector/graph/fact 权重
      fact_store.py           # knowledge_facts CRUD
      reranker.py             # bge-reranker 或 API
    orchestration/
      team_protocol.py        # debate_v1 配置执行
      pipeline_engine.py      # YAML step 执行器
  experts/_protocols/
    debate_v1.yaml
  skills/financial_audit/pipelines/
    audit_flow.yaml
  alembic/versions/005_knowledge_facts.py
```

### 5.2 我要修改的文件

| 文件 | 改动 |
|------|------|
| `rag/hybrid.py` | 接入 query_router + reranker |
| `rag/index_router.py` | table_row / fact 路由 |
| `memory/manager.py` | fact 命中注入 context |
| `agent/orchestrator.py` | team_protocol 分支替代硬编码 team class |
| `skills/executor.py` | pipeline_engine；hybrid fallback |
| `ingestion/pdf/` | 扫描路径 + 表格路径并入主 Job |
| `frontend/KnowledgeView.vue` | 表格/低质量文档标记 |

### 5.3 实现顺序

1. `table_extractor.py` + table 存 `knowledge_tables`  
2. `table_chunker.py` → summary + row chunks → index  
3. `fact_store.py`：从 table row 抽 (company, metric, period, value)  
4. Neo4j VALUE 边写入  
5. `ocr_pipeline.py` 接入 scanned PDF  
6. `query_router.py`：关键词+规则 intent；fact 问题走 SQL  
7. `reranker.py` 接在 hybrid 召回后  
8. `pipeline_engine.py`：builtin/tool/llm 三类 step  
9. `audit_flow.yaml` + financial_audit hybrid  
10. `team_protocol.py` + `debate_v1.yaml` 替换 debate 入口  
11. 评测集 20 题财务问答回归  

### 5.4 本批完成标准

- [ ] 含资产负债表 PDF：「货币资金」可答且带 page 引用  
- [ ] fact 表命中时 LLM context 含精确数值  
- [ ] hybrid+rerank 优于 batch1 基线（内部 20 题）  
- [ ] JSON 财报输入走 pipeline；纯文本走 ReAct  
- [ ] 财务评审委员会输出分角色流式（analyst/skeptic/judge）  
- [ ] 扫描 PDF OCR 后可检索（quality>0.75）  

### 5.5 本批不做

VLM 读图表、聊天 attachment vision

---

## 6. Batch 5 — VLM 图表 + 聊天 Vision

**目标**：PDF/图片中的图表被理解；用户聊天可直接发图。

### 6.1 我要新建的文件

```
backend/
  app/
    ingestion/media/
      vlm.py                  # chart/diagram prompt + structured JSON
      image_classifier_v2.py
    llm/
      vision.py               # multimodal message 构造
      providers.py            # supports_vision 元数据
    api/
      media.py                # GET original/thumb, reparse
  frontend/src/
    components/chat/AttachmentUpload.vue
    api/media.ts
```

### 6.2 我要修改的文件

| 文件 | 改动 |
|------|------|
| `ingestion/pdf/extractor.py` | 检测 figure region → 调 MediaAssetService |
| `ingestion/media/service.py` | chart → vlm.py |
| `llm/factory.py` | vision model 分支 |
| `api/chat.py` | 解析 `attachments[]` |
| `agent/runtime.py` | HumanMessage multimodal content |
| `frontend/ChatView.vue` | 拖图、预览、发送 attachments |
| `frontend/api/websocket.ts` | payload 带 attachments |
| `rag/index_router.py` | figure_summary + vlm structured → fact（高置信） |

### 6.3 实现顺序

1. `image_classifier_v2`：chart vs photo vs decorative  
2. `vlm.py`：chart structured prompt + JSON schema 校验  
3. PDF figure 切图 → parse_image → figure_summary chunk  
4. 低置信 vlm 数值不写 fact  
5. `vision.py`：OpenAI/Claude 格式统一  
6. `POST /api/media/upload` + chat attachment 流程  
7. WS message 带 attachments；无 vision 时降级 OCR 文本  
8. ChatView UI 拖图  
9. 评测：PDF 内柱状图描述 + 聊天截图问答  

### 6.4 本批完成标准

- [ ] PDF 内图表：问答描述趋势 + 引用 figure/page  
- [ ] 聊天发图：不先入知识库可单轮问答  
- [ ] 无 vision provider 配置时：降级 OCR 不 crash  
- [ ] decorative 图不进向量库  

---

## 7. 五批总表（我一页纸版）

| 批 | 后端核心 | 前端核心 | 设计文档 |
|:--:|----------|----------|----------|
| 1 | chunk_store, text_pipeline, Job, index_router | 解析状态, citation | 01§8-9, 02§3-5 |
| 2 | SKILL.md, expert YAML, runtime_policy, summon API | chip sync API | 03, 04 |
| 3 | pdf native, preprocessor, media OCR | PDF/图片上传 | 01§3-4, 05§5-10 |
| 4 | table, ocr scan, fact, query_router, pipeline, team_protocol | 表格文档标记 | 01§5-6, 02§6, 03§5, 04§4 |
| 5 | vlm, vision LLM, chat attachments | 拖图聊天 | 05§6-10 |

---

## 8. 每批结束我会怎么交付给你

| 交付项 | 说明 |
|--------|------|
| **代码** | 对应批次 PR 或 commit，message 含 `batch-N:` 前缀 |
| **迁移** | Alembic revision，附 rollback 说明 |
| **自测** | 本批「完成标准」勾选结果 |
| **演示** | 1 条你本地可复现操作（如「上传 xx.pdf 问 yy」） |
| **文档** | 更新 `docs/rag/README.md` 等现状说明「已实现至 Batch N」 |

---

## 9. 风险与我怎么控

| 风险 | 我的处理 |
|------|----------|
| PaddleOCR 环境难装 | Docker 化 OCR sidecar；开发期可用 Tesseract 兜底 |
| VLM 成本高 | 仅 `chart/diagram` 分类才调；相同 hash 缓存 |
| 批次 4 范围大 | 表格与 team_protocol 可拆 4a/4b，但你未要求细拆则一批交付 |
| 破坏现有聊天 | 每批跑现有 demo 账号回归：登录、对话、专家召唤、斜杠 |

---

## 10. 若你只说「开始开发」

我会从 **Batch 1** 第一步开始：

```
003_knowledge_chunks_jobs.py → chunk_store.py → chunker.py → text_pipeline.py → Job → 改 hybrid retrieve → 前端状态
```

不会先做 PDF，不会先做 VLM，不会跳过 chunk 主存。

---

## 11. 关联文档

- [Target 索引](./README.md)
- [产品向路线图（人周估算版）](./00-分批开发顺序与路线图.md) — 与本文互补：彼侧重排期，本文侧重**我实际写哪些文件**

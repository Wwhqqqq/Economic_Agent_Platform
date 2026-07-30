# Batch 1–5 数据库增量迁移说明

本版本在 `002_knowledge` 之后新增 **4 个 Alembic revision**，生产/本地均需执行 `alembic upgrade head`。

## 迁移链

| Revision | 文件 | 内容 |
|----------|------|------|
| `003_knowledge_chunks` | `003_knowledge_chunks_jobs.py` | `knowledge_chunks`、`ingest_jobs`；文档 `parse_status` / `parser_version` / `quality_score` / `ndm_uri` / `page_count` |
| `004_media_assets` | `004_media_assets_pdf_fields.py` | `media_assets` 表；文档 `source_type` / `mime_type` |
| `005_knowledge_facts` | `005_knowledge_facts.py` | `knowledge_tables`、`knowledge_facts`；文档 `doc_class` / `table_count` |
| `006_media_vlm` | `006_media_vlm.py` | `media_assets` 增加 VLM 字段：`vlm_caption`、`vlm_structured`、`thumbnail_uri`、`content_hash`、`parse_status` 等 |

**Head revision：** `006_media_vlm`

## 本地开发（Windows / macOS / Linux）

```bash
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
python -m alembic current    # 应显示 006_media_vlm (head)
```

Windows PowerShell 也可：

```powershell
.\deploy\migrate-local.ps1
```

## 腾讯云生产（Docker）

已有 `one-click-deploy` 环境，直接：

```bash
cd /opt/apps/agent-platform
bash deploy/incremental-update.sh
```

脚本会自动：`git pull` → `docker compose build migrate,backend,gateway` → **`alembic upgrade head`** → 重启 backend/gateway。

## 回滚（仅紧急情况）

按相反顺序 downgrade，**会删表/删列，请先备份 MySQL**：

```bash
cd backend
python -m alembic downgrade 005_knowledge_facts   # 回退 006
python -m alembic downgrade 004_media_assets      # 回退 005
python -m alembic downgrade 003_knowledge_chunks  # 回退 004
python -m alembic downgrade 002_knowledge         # 回退 003
```

## 部署后自检

```bash
# 迁移版本
docker compose -f deploy/docker-compose.prod.yml --project-directory . run --rm migrate alembic current

# 健康检查
curl -sf http://127.0.0.1:8082/health

# 后端冒烟（可选，在 backend 目录）
python scripts/smoke_test_apis.py http://127.0.0.1:8000
```

## 对象存储目录

Batch 1+ 使用 `backend/data/objects/` 存放上传原文件与 NDM；Batch 5 会话 summon 状态在 `backend/data/sessions/`。这两目录为**运行时数据**，已在 `.gitignore` 中排除，部署后自动创建。

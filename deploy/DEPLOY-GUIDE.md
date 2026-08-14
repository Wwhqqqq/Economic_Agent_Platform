# Agent Platform 生产部署指南（零差错版）

> 目标：**所有 Docker 容器正常运行**，**会员专享 RAG 知识库 18 篇全部灌库、切片、可检索**。

---

## 一、架构概览

| 组件 | 容器名 | 说明 |
|------|--------|------|
| MySQL | 复用宿主机已有 MySQL 容器 | 业务库 `agent_platform` |
| Redis | `agent-prod-redis` | 会话/缓存 |
| ChromaDB | `agent-prod-chromadb` | 向量检索（**必须 HTTP 模式，勿用本地 PersistentClient**） |
| Neo4j | `agent-prod-neo4j` | 知识图谱 |
| Backend | `agent-prod-backend` | FastAPI + RAG |
| Gateway | `agent-prod-gateway` | Nginx 静态前端 + 反代 API |
| Migrate | `agent-prod-migrate` | Alembic 一次性迁移 |

对外端口：**8082**（默认，可改 `DEPLOY_PORT`）

---

## 二、服务器首次部署

### 前置条件

1. Ubuntu 服务器，已安装 Docker + Docker Compose v2
2. 已有 **MySQL 8** Docker 容器（或本机 MySQL）
3. GitHub **PlatformAgent** Deploy Key 已安装（见 `deploy/SSH-RECOVERY.md`）
4. 准备好 `DEEPSEEK_API_KEY`

### 步骤

```bash
# 1. SSH 登录服务器
ssh ubuntu@你的服务器IP

# 2. 首次全量部署
export DEEPSEEK_API_KEY="sk-xxxx"
export MYSQL_PASSWORD="你的MySQL密码"
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Wwhqqqq/Economic_Agent_Platform/main/deploy/ssh-pull-deploy.sh)" -- --first

# 或在已克隆目录：
cd /opt/apps/agent-platform
export DEEPSEEK_API_KEY="sk-xxxx"
export MYSQL_PASSWORD="你的MySQL密码"
bash deploy/ssh-pull-deploy.sh --first
```

首次脚本会自动：

1. 克隆 `main` 分支
2. 生成 `.env`（JWT、Neo4j 密码等）
3. 创建 MySQL 库 `agent_platform`
4. `docker compose up -d --build` 启动全部容器
5. Alembic `upgrade head`
6. 健康检查 `/health`

### 3. RAG 知识库灌库（**必做**）

```bash
cd /opt/apps/agent-platform
bash deploy/post-deploy-rag.sh
```

该脚本会：

- 拉起 Redis / Chroma / Neo4j
- 执行 `python -m scripts.seed_member_knowledge`（18 篇会员专享会计/财务语料）
- 写入 MySQL + Chroma + Neo4j
- 自动验证：member 文档数 ≥ 15、Chroma 向量 ≥ 50

强制重建索引：

```bash
FORCE_SEED=1 bash deploy/post-deploy-rag.sh
```

### 4. 全栈验证

```bash
bash deploy/verify-stack.sh
```

输出 `[ALL OK]` 即表示容器、API、RAG 均正常。

---

## 三、日常增量更新

```bash
cd /opt/apps/agent-platform
bash deploy/ssh-pull-deploy.sh
# 等价于 git pull + incremental-update.sh
```

更新后**若包含知识库语料变更**，请执行：

```bash
bash deploy/post-deploy-rag.sh
# 或强制重建
FORCE_SEED=1 bash deploy/post-deploy-rag.sh
```

---

## 四、本地开发（Windows / Mac）

### 1. 启动 Docker 基础设施

**必须先启动 Docker Desktop**，再：

```bash
cd agent-platform
docker compose up -d
docker compose ps   # 全部应为 running / healthy
```

`.env` 关键项（使用 docker-compose 时）：

```env
DATABASE_URL=mysql+aiomysql://root:你的密码@localhost:3306/agent_platform?charset=utf8mb4
REDIS_URL=redis://localhost:6379/0
CHROMA_HOST=localhost
CHROMA_PORT=8001
NEO4J_URI=bolt://localhost:7688
NEO4J_PASSWORD=changeme
```

> 注意：Neo4j 映射端口为 **7688**（非 7687），与 `docker-compose.yml` 一致。

### 2. 后端 + 前端

```bash
cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

### 3. 本地灌库

```bash
cd backend
python -m scripts.seed_member_knowledge
```

验证：`GET /api/knowledge/documents/member`（需会员账号）

---

## 五、RAG 知识库来源

| 路径 | 说明 |
|------|------|
| `data/member_knowledge/*.md` | 18 篇结构化摘要（CAS、审计、税务等） |
| `data/member_knowledge/manifest.json` | 文档清单与权威来源 |
| `data/member_knowledge/SOURCES.md` | 知识来源说明 |

灌库脚本：`backend/scripts/seed_member_knowledge.py`

---

## 六、故障排查

| 现象 | 处理 |
|------|------|
| Chroma `KeyError: _type` | 删除旧本地持久化目录，改用 Docker Chroma HTTP：`CHROMA_HOST=localhost CHROMA_PORT=8001` |
| Redis 连接失败 | `docker compose up -d redis`，检查 `REDIS_URL` |
| Neo4j 连接失败 | 检查 `NEO4J_URI` 端口（Docker 7688），密码与 `NEO4J_AUTH` 一致 |
| 会员库为空 | 运行 `bash deploy/post-deploy-rag.sh` |
| `/health` degraded | 查看 `curl localhost:8082/health` 中 chroma/neo4j/mysql 字段 |
| GitHub SSH 失败 | 见 `deploy/SSH-RECOVERY.md` |

查看日志：

```bash
docker compose -f deploy/docker-compose.prod.yml -f deploy/docker-compose.prod.external-mysql.yml --project-directory . logs -f backend
```

---

## 七、部署检查清单

- [ ] Docker Desktop / Docker Engine 运行中
- [ ] MySQL 库 `agent_platform` 已创建
- [ ] `.env` 中 `DEEPSEEK_API_KEY`、`DATABASE_URL`、`NEO4J_PASSWORD` 正确
- [ ] `docker compose ps` 全部 running
- [ ] `curl http://服务器:8082/health` → status healthy/degraded（chroma+neo4j up）
- [ ] `bash deploy/post-deploy-rag.sh` → `[VERIFY OK]`
- [ ] 会员用户聊天可检索会计准则相关内容

---

## 八、相关脚本索引

| 脚本 | 用途 |
|------|------|
| `deploy/ssh-pull-deploy.sh` | SSH 拉代码 + 增量/首次部署 |
| `deploy/one-click-deploy.sh` | 首次全量部署 |
| `deploy/incremental-update.sh` | 增量更新 |
| `deploy/post-deploy-rag.sh` | **RAG 灌库 + 验证** |
| `deploy/verify-stack.sh` | 全栈验证 |
| `backend/scripts/seed_member_knowledge.py` | 会员知识库灌库 CLI |

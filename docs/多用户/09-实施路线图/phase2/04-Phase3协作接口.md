# 04 — Phase 3 协作接口（并行开发约定）

Phase 2 与 Phase 3 **可以并行**，但必须在开工前对齐本文档，避免两人改同一逻辑却不兼容。

---

## 1. 并行可行性结论

| 维度 | 结论 |
|------|------|
| 业务依赖 | Phase 3 会员库检索 **依赖** Phase 2 的 filter 框架（K-04）；门控/配额/API **不依赖** Phase 2 |
| 文件冲突 | `hybrid.py`、`memory/manager.py`、`knowledge.py` 为高发区；按下文 ownership 划分 |
| 推荐节奏 | Phase 2 先合并 **Step 2 filter 签名**（1～2 天）后，Phase 3 可全面并行 |

---

## 2. 文件 Ownership

| 文件 / 模块 | Phase 2 Owner | Phase 3 Owner | 规则 |
|-------------|---------------|---------------|------|
| `app/rag/tenant_filter.py` | **P2 创建** | P3 仅加 member 分支 | P2 合并前 P3 不建同名文件 |
| `app/rag/hybrid.py` | P2 retrieve/add/delete/list | P3 不改签名，只扩展 filter 内部 | 冲突时 P2 优先 |
| `app/rag/vector_store.py` | P2 where filter | P3 复用 | |
| `app/rag/knowledge_graph.py` | P2 user filter | P3 member filter | |
| `app/api/knowledge.py` | P2 CRUD + 归属 | P3 配额钩子 + member 列表分区 | P3 在 PR 中加 `check_quota` |
| `app/memory/manager.py` | P2 user_id 透传 | P3 确保 user_type 传入 retrieve | P2 预留参数 |
| `app/services/membership*.py` | — | **P3 独占** | P2 不建 |
| `app/api/membership.py` | — | **P3 独占** | |
| `app/api/chat.py` WS 鉴权 | P2 已完成 | P3 会员 mode 门控 | 各改不同函数块 |
| `app/agent/orchestrator.py` | P2 skill context | P3 require_member 门控 | 协调合并 |
| `frontend/KnowledgeView.vue` | P2 我的文档 | P3 会员专享 Tab | 分区改 |
| `frontend/ChatView.vue` 等 | — | P3 加锁 UI | P2 不碰 |

---

## 3. 核心接口约定（双方必须遵守）

### 3.1 RAG 检索

```python
# app/rag/hybrid.py — 签名（Phase 2 定稿，Phase 3 不破坏）

def retrieve(
    self,
    query: str,
    top_k: int = 5,
    mode: Literal["vector", "graph", "hybrid"] = "hybrid",
    *,
    user_id: int | None = None,
    user_type: str = "regular",
    rrf_k: int | None = None,
) -> list[Document]: ...
```

**Phase 2 语义**：
- filter = `(user_id=self AND visibility=private)`
- `user_type` 传入但 **不改变** filter

**Phase 3 语义**（在 `tenant_filter.build_retrieval_filter` 内扩展）：
- `user_type == "member"` 且未过期：
  - filter = `(user_id=self AND visibility=private) OR (visibility=member)`
- 普通用户：**禁止** OR member 分支

### 3.2 知识写入

```python
def add_knowledge(
    self,
    content: str,
    doc_id: str,
    *,
    user_id: int,
    visibility: Literal["private", "member"] = "private",
    metadata: dict | None = None,
    entities: list[dict] | None = None,
) -> dict: ...
```

- Phase 2：API 仅允许 `visibility=private`
- Phase 3：运维灌库脚本调用 `visibility=member`, `user_id=None`（MySQL 行 user_id NULL）

### 3.3 MemoryManager

```python
async def load_context_bundle(
    self,
    session_id: str,
    user_input: str,
    system_prompt: str | None = None,
    *,
    user_id: int | None = None,
    user_type: str = "regular",
    context_strategy: dict | None = None,
) -> dict: ...
```

- Phase 2：实现 user_id 全链路
- Phase 3：将 `user_type` 传入 `hybrid.retrieve`（R-04）

### 3.4 配额钩子（Phase 3 实现，Phase 2 留位）

```python
# app/services/quota_service.py — Phase 3 新建

async def check_quota(action: str, user_id: int, user_type: str) -> None:
    """超限 raise HTTPException 429"""
    ...
```

Phase 2 在 `knowledge_service.upload` 与 `chat_session_service.create` 留注释：

```python
# TODO(phase3): await check_quota("document", user_id, user_type)
```

**Phase 2 禁止实现配额逻辑**，避免与 Phase 3 冲突。

### 3.5 会员门控（Phase 3 独占）

```python
# app/services/auth.py — 已存在
async def require_member(user: UserContext = Depends(get_current_user)) -> UserContext: ...
```

Phase 3 挂到：Plan-Execute WS、Multi-Agent、高阶 skill execute。  
Phase 2 **不调用** require_member。

---

## 4. 数据库分工

| 表 | Phase 2 | Phase 3 |
|----|---------|---------|
| `knowledge_documents` | **创建表**；private 行 | member 行（灌库）；不改表结构 |
| `user_llm_settings` | 不建 | 建表 + API |
| `membership_orders` / `membership_codes` | 不建 | 可选建表 |

Alembic：**Phase 2 出 002**；Phase 3 出 003（user_llm_settings 等），避免同一 revision 文件两人改。

---

## 5. 分支与合并策略

```
main
 ├── feature/phase2-rag-isolation    （P2 负责人）
 └── feature/phase3-membership       （P3 负责人，基于 main 或 phase2 Step2 合并点）
```

**推荐**：
1. P2 的 `tenant_filter` + `retrieve` 签名 **优先合并 main**
2. P3 每日 rebase main；改 filter 时只改 `build_retrieval_filter` 的 member 分支
3. 合并冲突由 P2 review filter 相关 hunk

---

## 6. 联调检查点

| 检查点 | 触发条件 | 参与人 | 验证内容 |
|--------|----------|--------|----------|
| CP-1 | P2 Step 2 合并 main | P2 + P3 | P3 本地 rebase 后 import 无报错 |
| CP-2 | P2 全部合并 | P2 + P3 | 用例 2 通过 + P3 开始 member 灌库 |
| CP-3 | P3 member 检索完成 | P2 + P3 | 用例 3～6 通过 |

---

## 7. Phase 3 组员无 Docker 的影响

| Phase 3 工作 | 是否需要 Docker | 无 Docker 替代 |
|--------------|-----------------|----------------|
| require_member / membership API | 否（MySQL 即可） | 本地 MySQL + uvicorn |
| 配额 / 过期降级 | 否 | 改 MySQL users 表验证 |
| 前端会员 UI | 否 | npm run dev |
| 会员库灌库 + RAG E2E | 是（Chroma/Neo4j） | 共用测试服；或 Chroma 嵌入式 |
| JWT 黑名单 | Redis | 可 Phase 3 后期再做 |

**结论**：无 Docker **不阻塞** Phase 3 大部分开发；会员 RAG 全链路需 **CP-2 联调** 时用共享环境。

---

## 8. 双方签字确认（复制使用）

```
Phase 2 / Phase 3 接口对齐确认

retrieve 签名：已确认 / 待修订 ___
tenant_filter 模块由 Phase 2 创建：是
Phase 3 不改 retrieve 签名，仅扩展 filter：是
Alembic 002(P2) / 003(P3) 分开：是

Phase 2 负责人：________  日期：________
Phase 3 负责人：________  日期：________
```

# 06 — 记忆与 RAG 隔离

## 1. 隔离总览

原则不变：**所有私有数据带 user_id**；在此基础上增加 **visibility=member 的会员专享知识库**，仅会员 RAG 可检索。

```
普通用户 RAG 范围：     仅 private 且 user_id = self
会员用户 RAG 范围：     private(user_id=self) ∪ member(visibility=member)
```

记忆三层（短期 / 长期 / 情景）**与会员无关**，均严格 user_id 隔离；会员的增值在「平台 curated 知识」与「高级 Agent」，不在读取他人记忆。

## 2. 短期 / 长期 / 情景记忆

（与前一版相同：MySQL 会话消息、Chroma long_term user_id filter、Neo4j 复合键 user_id+name。）

**会员 vs 普通**：记忆逻辑无差异；会员可配置更高 `max_history` 或开启长期记忆（普通用户关闭长期记忆可选）。

## 3. RAG 知识库

### 3.1 私有知识库（两类用户均可，配额不同）

```
上传 → visibility=private, user_id=owner
检索 → user_id = self AND visibility = private
删除 → owner only
```

### 3.2 会员专享知识库

```
灌库（运维脚本）→ visibility=member, user_id=NULL
                  → Chroma + Neo4j 同步

普通用户检索：
  filter: user_id=self AND visibility=private
  （不包含 member）

会员用户检索：
  filter: (user_id=self AND visibility=private)
       OR visibility=member
```

### 3.3 Hybrid RRF

向量路与图谱路**各自**按 user_type 应用 filter 后再融合；禁止普通用户路径传入 member 条件。

### 3.4 列表 API

| 用户类型 | GET /api/knowledge/documents |
|----------|------------------------------|
| regular | 仅自己的 private |
| member | 自己的 private + member 库列表（member 项只读、不可删） |

## 4. MemoryManager 与 user_type

```
load_context_bundle(session_id, user_id, user_type, user_input, ...):
  hybrid.retrieve(query, user_id, user_type)
  long_term.recall(query, user_id)
  episodic.recall(keywords, user_id)
  // member 库是否并入由 retrieve 内部根据 user_type 决定
```

## 5. file_reader 隔离

- 用户上传：`./data/uploads/{user_id}/`
- 会员专享源文件：运维目录，不映射到用户 upload 路径

## 6. 测试用例（更新）

| # | 场景 | 期望 |
|---|------|------|
| 1 | A 的 session，B 连接 WS | 403 |
| 2 | A 私有 doc，B 搜索 | 无 A 数据 |
| 3 | 普通用户搜索会员库关键词 | 无 member 库结果 |
| 4 | 会员用户搜索会员库关键词 | 有结果 |
| 5 | 普通用户 DELETE member 文档 | 403 |
| 6 | 会员过期后立即搜会员库 | 无 member 结果（已降级） |
| 7 | A 删 session 不影响 B | ✓ |

## 7. 相关文档

- [04 — 权限与租户隔离](../04-权限与租户隔离/README.md)
- [RAG 模块（现有）](../../rag/README.md)

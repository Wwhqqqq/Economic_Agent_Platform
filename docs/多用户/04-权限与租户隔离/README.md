# 04 — 权限与租户隔离

## 1. 租户模型

### 1.1 行级隔离（不变）

所有用户共用同一 MySQL 库，通过 `user_id` 区分私有数据；Chroma / Neo4j 通过 metadata 携带 `user_id`。

### 1.2 用户类型（替代 RBAC 多角色）

本系统**不做** admin / user / guest 等多角色 RBAC，而是：

```
user_type ∈ { regular, member }
```

权限 = **用户类型门控** + **资源归属校验** + **配额限制**。

## 2. 两级用户权限矩阵

### 2.1 数据与资源

| 资源 / 操作 | 普通用户 | 会员用户 |
|-------------|----------|----------|
| 自己的会话 CRUD | ✓ | ✓ |
| 他人的会话 | ✗ | ✗ |
| 自己的私有知识库 CRUD | ✓（配额内） | ✓（配额内） |
| 他人的私有知识库 | ✗ | ✗ |
| 检索会员专享知识库 | ✗ | ✓ |
| 删除会员专享知识库 | ✗ | ✗（仅运维） |
| 自己的 LLM 设置 | 受限 | ✓ |
| 查看自己的审计日志 | ✓ | ✓ |
| 查看他人审计日志 | ✗ | ✗ |

### 2.2 Agent 与技能

| 能力 | 普通用户 | 会员用户 |
|------|----------|----------|
| execution_mode: reasoning_action | ✓ | ✓ |
| execution_mode: adaptive → ReAct | ✓ | ✓ |
| execution_mode: task_orchestration | ✗ → 403 | ✓ |
| execution_mode: collaborative_decision | ✗ → 403 | ✓ |
| skill: document_analysis | ✓ | ✓ |
| skill: financial_audit | ✗ | ✓ |
| skill: data_visualization | ✗ | ✓ |
| Tools 目录浏览 | ✓ | ✓ |
| web_search / calculator / file_reader | ✓ | ✓ |
| accounting 全套工具 | 随技能 | ✓ |
| code_executor | ✗ | ✓（可全局关闭） |

### 2.3 门控实现位置

| 层级 | 做法 |
|------|------|
| API / WS 入口 | 校验 mode、skill 是否 member-only |
| AgentOrchestrator | `_select_mode` 前检查 user_type |
| Skills API execute | 高阶 skill 需 member |
| RAG retrieve | 是否合并 member 库取决于 user_type |
| 配额 | 创建 session / upload 前检查计数 |

**普通用户尝试会员功能时**：HTTP 403，body `{ "code": "MEMBERSHIP_REQUIRED", "message": "该功能需开通会员" }`；WS 发 `error` 事件。

## 3. 权限检查层次

```
Layer 1: 认证 — 是否登录（AUTH_ENABLED=true 时）
Layer 2: 用户类型 — 是否 member（功能门控）
Layer 3: 资源归属 — session/doc 是否属于当前 user_id
Layer 4: 配额 — 是否超限
Layer 5: 字段安全 — API Key 不写回明文
```

**资源归属（Layer 3）**示例：

```
session = session_repo.get(session_id)
if session.user_id != ctx.user_id:
    raise 403
```

不再存在 `is_admin_for(resource)` 分支。

## 4. 知识库可见性模型

| visibility | 含义 | 谁可检索 | 谁可删除 |
|------------|------|----------|----------|
| **private** | 用户自建 | 仅 owner | 仅 owner |
| **member** | 会员专享（平台灌库） | 仅 member | 仅运维脚本 |

**普通用户 RAG filter**：

```
user_id = self AND visibility = private
（不包含 member 库）
```

**会员用户 RAG filter**：

```
(user_id = self AND visibility = private)
OR visibility = member
```

Chroma / Neo4j 检索在应用层按上述逻辑构造 filter，**禁止**普通用户 query 中带 member visibility。

## 5. 会员开通与降级

### 5.1 开通路径（无管理端）

| 方式 | 说明 |
|------|------|
| 支付 Webhook | 验签后 `UPDATE users SET user_type='member', membership_expires_at=?` |
| 兑换码 API | 用户输入码，后端校验一次性码表 |
| 运维脚本 | 手动 UPDATE，用于内测赠送会员 |

### 5.2 过期降级

每次 `get_current_user` 或登录时：

```
if user_type == member and expires_at < now():
    user_type = regular
    persist
```

JWT 内 `user_type` 在 Token 签发时写入；过期后需重新登录或 Refresh 以刷新 Token。

## 6. API 鉴权分类

| 类型 | 示例 | 策略 |
|------|------|------|
| 公开 | `/health`, `/api/auth/login`, `/api/auth/register` | 无 Token |
| 已登录 | `/api/sessions`, WS chat | 有效 Token |
| 仅会员 | Plan-Execute WS mode, financial_audit | user_type == member |
| 资源级 | DELETE session | 归属 user_id |

依赖注入：

```
get_current_user → UserContext(user_id, username, user_type, membership_expires_at)
require_member() → 403 if user_type != member
check_quota(action) → 429 if exceeded
```

## 7. 数据隔离清单

| 模块 | 隔离方式 |
|------|----------|
| chat_sessions / messages | WHERE user_id |
| knowledge private | user_id + visibility=private |
| knowledge member | visibility=member，检索侧按 user_type |
| Chroma / Neo4j | metadata user_id + visibility |
| long_term_memory | metadata user_id |
| user_llm_settings | user_id（建议仅 member 可写） |
| audit_logs | actor_user_id = self |

## 8. 越权场景与防护

| 攻击 | 防护 |
|------|------|
| 普通用户 WS 传 mode=multi_agent | 服务端 require_member |
| 普通用户检索 member 库 | retrieve 不传 member filter |
| 遍历他人 session_id | 归属校验 |
| 伪造 user_type 于 WS body | 只信 JWT |
| 过期会员继续用高级功能 | expires 校验 + Token 刷新 |

## 9. 工具与文件隔离

- `file_reader` 路径：`./data/uploads/{user_id}/`
- 普通用户不可触发 code_executor
- 会员专享知识库文件不在用户 upload 目录，由运维导入专用路径或直写 Chroma

## 10. 相关文档

- [01 — 需求与现状分析](../01-需求与现状分析/README.md)
- [06 — 记忆与 RAG 隔离](../06-记忆与RAG隔离/README.md)

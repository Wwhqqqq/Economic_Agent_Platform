# 05 — 数据模型与 MySQL 设计

## 1. 设计原则

（InnoDB、utf8mb4、索引等与原先相同，此处从略。）

**用户类型字段统一命名 `user_type`**，取值 `regular` | `member`。

## 2. ER 关系

```
users 1 ── N chat_sessions 1 ── N chat_messages
users 1 ── N knowledge_documents (visibility=private)
users 1 ── 0..1 user_llm_settings
users 1 ── N refresh_tokens
users 1 ── N audit_logs
users 1 ── N membership_orders（可选，支付记录）

knowledge_documents (visibility=member, user_id=NULL) ← 运维灌库，无 owner
membership_codes（可选，兑换码）
system_settings（配额、功能开关，运维维护）
```

**无 admin 用户表、无 admin 角色字段。**

## 3. 表结构

### 3.1 users

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | |
| username | VARCHAR(64) UNIQUE | |
| email | VARCHAR(255) UNIQUE NULL | |
| password_hash | VARCHAR(255) | |
| **user_type** | ENUM('regular','member') | **默认 regular** |
| **membership_expires_at** | DATETIME NULL | 会员到期；NULL=非会员或无期限 |
| status | ENUM('active','disabled') | disabled 由运维设置 |
| login_attempts | INT | |
| locked_until | DATETIME NULL | |
| last_login_at | DATETIME NULL | |
| created_at / updated_at | DATETIME | |

索引：`username`, `(user_type, membership_expires_at)`

### 3.2 membership_orders（可选）

记录支付流水，便于对账：

| 列 | 说明 |
|----|------|
| id | PK |
| user_id | FK |
| external_order_id | 支付平台单号，UNIQUE |
| plan | 月卡/年卡 |
| amount | 分 |
| paid_at | |
| expires_at | 本次购买延长的到期时间 |

### 3.3 membership_codes（可选）

| 列 | 说明 |
|----|------|
| code | UNIQUE |
| duration_days | |
| used_by_user_id | NULL |
| used_at | NULL |

### 3.4 chat_sessions / chat_messages

（结构同前，无变化。）

### 3.5 knowledge_documents

| 列 | 类型 | 说明 |
|----|------|------|
| id | CHAR(36) PK | |
| user_id | BIGINT NULL | private 必填；member 库为 NULL |
| **visibility** | ENUM('private','member') | |
| title / filename / chunk_count | | |
| created_at / deleted_at | | |

索引：`(user_id, visibility)`, `(visibility)`

### 3.6 user_llm_settings

仅会员建议写入；普通用户可无行或只读平台默认。

| 列 | 说明 |
|----|------|
| user_id | PK FK |
| default_provider | |
| providers_json | 含加密 api_key |

### 3.7 system_settings

运维维护的键值配置，**应用只读**：

| key 示例 | value 示例 |
|----------|------------|
| quota.regular.max_sessions | 20 |
| quota.member.max_sessions | 500 |
| quota.regular.max_documents | 10 |
| feature.code_executor_member_only | true |

无 `updated_by admin` 字段；可留 `updated_at` + 备注。

### 3.8 audit_logs

| 列 | 说明 |
|----|------|
| actor_user_id | |
| action | auth.login, membership.activated, knowledge.upload |
| ... | |

用户 API 仅 `WHERE actor_user_id = self`。

## 4. Chroma / Neo4j 映射

| visibility | Chroma metadata | Neo4j Document |
|------------|-----------------|----------------|
| private | user_id=owner, visibility=private | 同左 |
| member | user_id 空或 0, visibility=member | 同左 |

## 5. 迁移策略

| 现有 | 迁移 |
|------|------|
| .env 单账号 | 可建一个 member 测试账号，或废弃 |
| 内存会话 | 丢弃或 user_id=0 |
| 旧 Chroma 文档 | visibility=member（作会员专享样例）或删除 |
| settings.json | → system_settings + 测试会员 user_llm_settings |

## 6. 相关文档

- [04 — 权限](../04-权限与租户隔离/README.md)
- [06 — 记忆与 RAG](../06-记忆与RAG隔离/README.md)

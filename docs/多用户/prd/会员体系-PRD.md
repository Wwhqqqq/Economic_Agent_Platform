# PRD — 会员体系（完整版）

> **版本**：1.0  
> **日期**：2026-08-11  
> **状态**：待评审  
> **优先级**：P1（Phase 3 核心交付）  
> **路由**：`/membership`、`/membership/redeem`；关联 `/`、`/skills`、`/knowledge`、`/settings`  
> **关联文档**：[04 — 权限与租户隔离](../04-权限与租户隔离/README.md)、[05 — 数据模型](../05-数据模型与MySQL设计/README.md)、[11 — 页面与功能清单](../11-页面与功能清单/README.md)

---

## 1. 背景与目标

### 1.1 背景

Agent Platform 已完成 Phase 0/1/2 基础能力：

- MySQL 用户体系、`regular` / `member` 两级用户类型
- JWT 鉴权、WebSocket 握手鉴权、会话归属校验
- 前端会员徽章、会员中心占位页、模型配置会员锁定（**唯一已生效的后端门控**）
- 执行模式：Auto（`adaptive`）、Medium（`reasoning_action`）、Plan（`task_orchestration`）、Multi-Agent（`collaborative_decision`）

**当前缺口**：会员商业化门控大多停留在设计文档，普通用户 today 可实际使用 Plan-Execute、Multi-Agent、高阶技能，与产品定位不符。

### 1.2 产品定位

采用 **Freemium + 订阅会员** SaaS 模型：

| 类型 | 标识 | 定位 |
|------|------|------|
| **普通用户** | `regular` | 注册默认；体验核心对话与基础能力 |
| **会员用户** | `member` | 付费/兑换/运维开通；完整 Agent 能力与会员知识库 |

**明确不做**：应用内管理后台、admin 角色、组织 RBAC、完整收银台 UI（Phase 4 仅 Webhook + 外链）。

### 1.3 产品目标

| 目标 | 说明 | 衡量 |
|------|------|------|
| **可区分** | 普通/会员能力差异清晰可感知 | 权限矩阵 100% 服务端 enforced |
| **可转化** | 触达会员功能时有明确升级引导 | 403/WS error → 升级弹窗转化率可统计 |
| **可开通** | 支持 Webhook 支付、兑换码、运维脚本三种开通路径 | 开通后 5s 内前端刷新会员态 |
| **可过期** | 到期自动降级，不残留会员能力 | 过期账号 Plan 模式 403 |
| **可配额** | 会话/文档/日消息按 tier 限制 | 超限返回 429 + 友好文案 |
| **可验收** | 每项能力有自动化测试用例 | Phase 3 验收清单全绿 |

### 1.4 核心产品决策（本 PRD 权威定义）

以下决策与早期设计文档略有差异，**以本 PRD 为准**：

| 决策项 | 本 PRD 定义 | 说明 |
|--------|-------------|------|
| 普通用户可见执行模式 | **仅 Auto** | UI 不暴露 Medium/Plan 选项 |
| Auto 内部路由（普通用户） | **固定 → Medium（ReAct）** | 不升 Plan、不升 Multi-Agent |
| Auto 内部路由（会员） | **全路由** | 关键词可升 Plan / Multi-Agent |
| 会员手动可选模式 | Auto + Medium + Plan | Multi-Agent 通过 Auto 路由或专家召唤 |
| 定价 | 月卡 / 年卡 / 7 天试用 | 具体金额可配置，初版可用占位 |
| 第三档 VIP | **不做** | 保持两级，降低复杂度 |

### 1.5 不在本次范围

- 按 Token 精确计费、用量账单明细
- 企业版 / 团队席位 / 组织订阅
- 应用内完整支付收银台（支付宝/微信 SDK 内嵌）
- OAuth / 企业 SSO
- 发票、退款自助流程（仅 Webhook 记录 + 运维处理）
- 管理员后台 UI

---

## 2. 用户与场景

### 2.1 目标用户

| 用户 | 描述 |
|------|------|
| **普通用户** | 注册体验者、学生、轻度使用者 |
| **会员用户** | 财务/审计从业者、需复杂任务编排的专业用户 |
| **即将过期会员** | 到期前 7 天需续费提醒 |
| **过期会员** | 曾付费，已自动降级为 regular |

### 2.2 核心场景

| 编号 | 场景 | 用户类型 | 期望结果 |
|------|------|----------|----------|
| S1 | 普通用户打开聊天页 | regular | 模式选择器仅显示 Auto；发送消息走 ReAct |
| S2 | 普通用户输入「请做财务审计报告」 | regular | Auto 不升 Plan；正常 ReAct 回复；可选轻提示「升级会员解锁任务编排」 |
| S3 | 普通用户通过 WS 伪造 Plan 模式 | regular | 服务端 403，`MEMBERSHIP_REQUIRED` |
| S4 | 普通用户点击财务审计技能 | regular | 前端锁定 + 后端 execute 403 |
| S5 | 普通用户上传第 11 份文档 | regular | 429 配额超限，引导升级 |
| S6 | 普通用户尝试配置个人 API Key | regular | 设置页只读 + 403（已实现，保持） |
| S7 | 用户完成支付 | regular→member | Webhook 更新 DB；下次请求/刷新 Token 后生效 |
| S8 | 会员用户使用 Plan 模式 | member | 任务拆解 → 逐步执行 → 汇总 |
| S9 | 会员用户检索知识库 | member | 私有库 + 会员专享库合并 RAG |
| S10 | 会员到期后登录 | expired member | 自动降级 regular；Plan 模式不可用 |
| S11 | 用户输入兑换码 | regular | 开通/延长会员，会员中心展示新到期日 |
| S12 | 新用户注册 | regular | 可选：赠送 7 天试用会员（可配置开关） |

---

## 3. 能力矩阵（权威）

### 3.1 执行模式

| 能力 | 普通用户 | 会员用户 | 门控位置 |
|------|----------|----------|----------|
| **Auto（adaptive）** | ✓ 唯一可见 | ✓ | 前端过滤选项 |
| Auto → Medium（ReAct） | ✓ 固定 | ✓ | orchestrator `_select_mode` |
| Auto → Plan | ✗ | ✓ | orchestrator + WS |
| Auto → Multi-Agent | ✗ | ✓ | orchestrator + WS |
| **Medium 手动选择** | ✗ UI 不可见 | ✓ | 前端 + WS |
| **Plan 手动选择** | ✗ | ✓ | 前端 + WS |
| 专家 `finance_reviewer`（默认 Plan） | ✗ 拦截 | ✓ | runtime_policy + WS |
| 专家 `finance_review_board`（Multi-Agent） | ✗ 拦截 | ✓ | 同上 |

### 3.2 技能与工具

| 能力 | 普通用户 | 会员用户 | `membership_required` |
|------|----------|----------|----------------------|
| `document_analysis` | ✓ | ✓ | false |
| `data_visualization` | ✗ | ✓ | true |
| `financial_audit` | ✗ | ✓ | true |
| web_search / calculator / file_reader | ✓ | ✓ | false |
| accounting 工具集 | 随技能 | ✓ | 随技能 |
| `code_executor` | ✗ | ✓ | true（可全局关闭） |

### 3.3 知识与记忆

| 能力 | 普通用户 | 会员用户 |
|------|----------|----------|
| 私有知识库 CRUD | ✓ | ✓ |
| 会员专享知识库 RAG | ✗ | ✓ |
| 长期记忆 | 关闭或 ≤50 条 | 开启，≤500 条 |

### 3.4 配置

| 能力 | 普通用户 | 会员用户 |
|------|----------|----------|
| 平台默认 LLM 对话 | ✓ | ✓ |
| 个人 LLM API Key 配置 | ✗ 只读 | ✓ 读写 |

### 3.5 配额（默认值，存 `system_settings`）

| 配额项 | key | 普通用户 | 会员用户 |
|--------|-----|----------|----------|
| 最大会话数 | `quota.{type}.max_sessions` | 20 | 500 |
| 知识库文档数 | `quota.{type}.max_documents` | 10 | 200 |
| 单文件大小（MB） | `quota.{type}.max_file_mb` | 5 | 20 |
| 每日 WS 消息数 | `quota.{type}.daily_messages` | 100 | 2000 |
| 长期记忆条数 | `quota.{type}.max_long_term_memories` | 0 | 500 |

超限 HTTP 状态码：**429**，body `{ "code": "QUOTA_EXCEEDED", "message": "...", "quota": "max_documents" }`。

---

## 4. 会员套餐与定价

### 4.1 套餐定义

| plan_id | 名称 | 时长 | 建议定价（可配置） | 说明 |
|---------|------|------|-------------------|------|
| `trial_7d` | 7 天体验 | 7 天 | ¥0 | 注册赠送，每用户限 1 次 |
| `monthly` | 会员月卡 | 30 天 | ¥59/月 | 标准订阅 |
| `yearly` | 会员年卡 | 365 天 | ¥499/年 | 约 7 折 |
| `redeem` | 兑换码 | 按码配置 | — | `duration_days` 来自码表 |

定价存 `system_settings` 或前端配置 JSON，**初版可展示占位价**，支付外链由运营配置。

### 4.2 到期时间计算规则

```
若当前非会员或已过期：
  membership_expires_at = now + duration
若当前有效会员续费：
  membership_expires_at = max(now, current_expires) + duration
```

始终设置 `user_type = 'member'`。

### 4.3 试用策略（可选，默认开启）

| 配置项 | key | 默认值 |
|--------|-----|--------|
| 注册赠送试用 | `membership.trial.enabled` | true |
| 试用天数 | `membership.trial.duration_days` | 7 |
| 每用户限一次 | `membership.trial.once_per_user` | true |

注册成功后若启用试用，写入 `user_type=member`、`membership_expires_at=now+7d`，并在会员中心标注「体验会员」。

---

## 5. 页面与交互

### 5.1 页面清单

| 页面 | 路由 | 优先级 | 说明 |
|------|------|--------|------|
| 会员中心 | `/membership` | P1 | 状态、权益、套餐、升级入口 |
| 兑换码 | `/membership/redeem` | P2 | 可合并为会员中心 Tab |
| 聊天页（改） | `/` | P1 | 模式加锁、升级弹窗、配额展示 |
| 技能页（改） | `/skills` | P1 | 会员专享标注 |
| 知识库（改） | `/knowledge` | P1 | 分区列表、配额提示 |
| 设置页（改） | `/settings` | P1 | 已有会员分支，联动 quota API |

### 5.2 会员中心 `/membership`

#### 5.2.1 布局结构

```
┌─────────────────────────────────────────────────┐
│ PageHeader: 会员中心                              │
├─────────────────────────────────────────────────┤
│ [MembershipBadge]  普通用户 / 会员用户             │
│ 标题：升级会员，解锁专业财务智能体能力 / 感谢您的支持  │
│ 到期时间：2027-06-30（会员可见）                    │
├─────────────────────────────────────────────────┤
│ 配额卡片（4 格）                                   │
│  会话 12/20  │  文档 3/10  │  今日消息 45/100     │
├─────────────────────────────────────────────────┤
│ 权益对比表（见 §5.2.3）                            │
├─────────────────────────────────────────────────┤
│ 套餐卡片 ×3（体验已用则隐藏）                       │
│  [月卡 ¥59]  [年卡 ¥499 推荐]  [兑换码]           │
├─────────────────────────────────────────────────┤
│ 常见问题折叠面板                                   │
└─────────────────────────────────────────────────┘
```

#### 5.2.2 状态分支

| 状态 | 主按钮 | 副操作 |
|------|--------|--------|
| 普通用户 | 「立即升级」→ 外链支付页 | 「我有兑换码」 |
| 体验会员（trial） | 「升级为正式会员」 | 显示「体验剩余 N 天」 |
| 有效会员 | 「续费」 | 「查看订单记录」（P2） |
| 即将过期（≤7 天） | 顶部 Banner 黄色提醒 | 同上 |

#### 5.2.3 权益对比表（固定文案）

| 能力 | 普通用户 | 会员 |
|------|----------|------|
| Auto 智能对话 | ✓ | ✓ |
| Plan 任务编排 | — | ✓ |
| Multi-Agent 协同决策 | — | ✓ |
| 财务审计 / 数据可视化技能 | — | ✓ |
| 会员专享知识库 | — | ✓ |
| 个人 LLM 配置 | — | ✓ |
| 会话 / 文档配额 | 基础 | 10 倍+ |

### 5.3 聊天页模式选择器

#### 5.3.1 普通用户

- 模式区域：**仅显示 Auto**，或显示为不可点击的标签「Auto · 智能推理」
- 不渲染 Medium / Plan 选项
- 若 localStorage 残留 `task_orchestration`，mount 时重置为 `adaptive`

#### 5.3.2 会员用户

```typescript
const executionModeOptions = [
  { label: 'Auto', value: 'adaptive', desc: '自动模式' },
  { label: 'Medium', value: 'reasoning_action', desc: '推理闭环' },
  { label: 'Plan', value: 'task_orchestration', desc: '任务编排' },
]
```

#### 5.3.3 升级引导弹窗 `UpgradePrompt.vue`

**触发条件**（任一）：

1. WS 收到 `{ type: "error", code: "MEMBERSHIP_REQUIRED" }`
2. 用户点击会员专享技能
3. 配额 429 且 quota 为 sessions/documents
4. （可选）复杂任务关键词被 Auto 降级时，底部 toast 轻提示

**弹窗内容**：

```
标题：该功能需要会员
正文：Plan 任务编排、Multi-Agent 协同、财务审计技能等专业能力需开通会员。
权益 bullet ×4
[ 立即升级 ]  [ 稍后再说 ]
```

点击「立即升级」→ `router.push('/membership')`。

### 5.4 技能页

- 卡片右上角：`会员专享` 标签（`membership_required: true`）
- 普通用户点击：不发起 execute，直接弹 UpgradePrompt
- 会员用户：正常流程

### 5.5 知识库页

| Tab | 普通用户 | 会员用户 |
|-----|----------|----------|
| 我的文档 | ✓ 可 CRUD | ✓ |
| 会员专享 | 锁定，展示样例标题 + 升级引导 | ✓ 只读列表 + RAG 可用 |

上传区展示：`已用 X / 上限 Y 份文档`。

### 5.6 全局会员徽章

位置：侧栏用户卡片、会员中心、设置页账号区。

组件：`MembershipBadge.vue`（已有，扩展 `trial` 变体）。

---

## 6. 接口设计

### 6.1 通用约定

**鉴权**：除 Webhook 外均需 `Authorization: Bearer <access_token>`。

**会员判断**：服务端以 DB 实时 `user_type` + `membership_expires_at` 为准；JWT 内 `user_type` 仅作缓存，过期降级后需 re-login 或 refresh。

**错误码**：

| code | HTTP | 说明 |
|------|------|------|
| `MEMBERSHIP_REQUIRED` | 403 | 需会员 |
| `QUOTA_EXCEEDED` | 429 | 配额超限 |
| `MEMBERSHIP_EXPIRED` | 403 | 会员已过期（可选，通常已降级） |
| `INVALID_REDEEM_CODE` | 400 | 兑换码无效 |
| `REDEEM_CODE_USED` | 400 | 兑换码已使用 |
| `WEBHOOK_SIGNATURE_INVALID` | 401 | Webhook 签名校验失败 |

### 6.2 GET `/api/membership/status`

**描述**：当前用户会员状态与权益摘要。

**响应 200**：

```json
{
  "user_type": "regular",
  "is_member": false,
  "membership_expires_at": null,
  "is_trial": false,
  "days_remaining": null,
  "benefits": {
    "execution_modes": ["adaptive"],
    "skills": ["document_analysis"],
    "member_knowledge": false,
    "personal_llm": false
  },
  "plans": [
    { "id": "monthly", "name": "会员月卡", "price_cents": 5900, "duration_days": 30 },
    { "id": "yearly", "name": "会员年卡", "price_cents": 49900, "duration_days": 365, "recommended": true }
  ],
  "upgrade_url": "https://pay.example.com/checkout?user_id=123"
}
```

`upgrade_url` 来自环境变量 `MEMBERSHIP_UPGRADE_URL`，未配置时返回 `null`，前端按钮显示「即将推出」。

### 6.3 GET `/api/membership/quota`

**描述**：配额使用量与上限。

**响应 200**：

```json
{
  "sessions": { "used": 12, "limit": 20 },
  "documents": { "used": 3, "limit": 10 },
  "daily_messages": { "used": 45, "limit": 100, "resets_at": "2026-08-12T00:00:00+08:00" },
  "long_term_memories": { "used": 0, "limit": 0 }
}
```

`limit: null` 表示无上限。

### 6.4 POST `/api/membership/redeem`

**请求**：

```json
{ "code": "FIN-AUDIT-2026" }
```

**响应 200**：

```json
{
  "success": true,
  "membership_expires_at": "2027-08-11T00:00:00+08:00",
  "message": "兑换成功，会员已延长 365 天"
}
```

**错误**：400 `INVALID_REDEEM_CODE` / `REDEEM_CODE_USED`。

### 6.5 POST `/api/membership/webhook`

**描述**：支付平台回调，**无 JWT**，HMAC 签名校验。

**请求头**：`X-Webhook-Signature: sha256=<hex>`

**请求体**：

```json
{
  "event": "payment.success",
  "order_id": "ext_order_12345",
  "user_id": 42,
  "plan": "yearly",
  "amount_cents": 49900,
  "paid_at": "2026-08-11T14:00:00+08:00"
}
```

**处理逻辑**：

1. 校验签名（密钥 `MEMBERSHIP_WEBHOOK_SECRET`）
2. 幂等：`external_order_id` UNIQUE，重复回调返回 200 不重复延期
3. 更新 `users.user_type`、`membership_expires_at`
4. 写入 `membership_orders`
5. 写入 `audit_logs`（action=`membership.activated`）

**响应 200**：`{ "ok": true }`

### 6.6 GET `/api/membership/orders`（P2）

当前用户最近 20 条支付记录，只读。

### 6.7 WebSocket 会员门控

**现有路径**：`WS /ws/chat/{session_id}?token=...`

**消息体扩展**（无变更，门控在服务端）：

```json
{
  "type": "message",
  "input": "请审计这份报表",
  "mode": "task_orchestration",
  "skill": "financial_audit",
  "provider": "deepseek",
  "model": "deepseek-chat"
}
```

**门控顺序**（在 `orchestrator.stream` 之前）：

```
1. normalize_execution_mode(mode)
2. resolve runtime_policy → 可能从 expert 推断 plan/multi_agent
3. membership_gate(user, resolved_mode, skill, expert_id)
4. daily_message quota
5. orchestrator.stream(...)
```

**WS 错误事件**：

```json
{
  "type": "error",
  "code": "MEMBERSHIP_REQUIRED",
  "message": "Plan 任务编排模式需开通会员",
  "upgrade_url": "/membership"
}
```

### 6.8 技能 API 扩展

**GET `/api/skills`** 每项增加：

```json
{
  "name": "financial_audit",
  "display_name": "财务审阅技能",
  "membership_required": true
}
```

**POST `/api/skills/{name}/execute`**：若 `membership_required && !user.is_member` → 403。

### 6.9 注册试用钩子

**POST `/api/auth/register`** 成功后，若 `membership.trial.enabled`：

- 设置 `user_type=member`，`membership_expires_at=now+trial_days`
- 响应 `is_trial: true`

---

## 7. 数据模型

### 7.1 已有表（沿用）

**users** — 见 [05 — 数据模型](../05-数据模型与MySQL设计/README.md)

### 7.2 新增表

#### membership_orders

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | |
| user_id | BIGINT FK | |
| external_order_id | VARCHAR(128) UNIQUE | 支付平台单号 |
| plan | VARCHAR(32) | monthly / yearly / trial_7d / redeem |
| amount_cents | INT | 金额（分），试用为 0 |
| paid_at | DATETIME | |
| expires_after | DATETIME | 本次购买后的到期时间 |
| source | ENUM | webhook / redeem / admin_script / trial |
| created_at | DATETIME | |

索引：`(user_id, created_at DESC)`

#### membership_codes

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | |
| code | VARCHAR(64) UNIQUE | 大小写不敏感 |
| duration_days | INT | |
| max_uses | INT DEFAULT 1 | 1=一次性 |
| use_count | INT DEFAULT 0 | |
| expires_at | DATETIME NULL | 码本身过期时间 |
| created_at | DATETIME | |

#### membership_redemptions（可选，审计用）

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT PK | |
| code_id | BIGINT FK | |
| user_id | BIGINT FK | |
| redeemed_at | DATETIME | |

### 7.3 system_settings 新增键

| key | 默认值 | 说明 |
|-----|--------|------|
| `quota.regular.max_file_mb` | 5 | |
| `quota.member.max_file_mb` | 20 | |
| `quota.regular.daily_messages` | 100 | |
| `quota.member.daily_messages` | 2000 | |
| `quota.regular.max_long_term_memories` | 0 | |
| `quota.member.max_long_term_memories` | 500 | |
| `membership.trial.enabled` | true | |
| `membership.trial.duration_days` | 7 | |
| `feature.code_executor_member_only` | true | |
| `membership.pricing.monthly_cents` | 5900 | |
| `membership.pricing.yearly_cents` | 49900 | |

### 7.4 Alembic

- **003_membership_tables.py**：membership_orders、membership_codes、membership_redemptions
- **004_membership_quota_settings.py**：seed 新 system_settings 键

---

## 8. 后端实现规范

### 8.1 模块结构（新建）

```
backend/app/services/
├── membership_service.py    # 开通、续期、状态查询
├── quota_service.py         # check_quota、get_usage
├── membership_gate.py       # 模式/技能/专家门控纯函数
└── redeem_service.py        # 兑换码逻辑

backend/app/api/
└── membership.py            # REST 路由
```

### 8.2 membership_gate.py（核心）

```python
MEMBER_ONLY_MODES = frozenset({"task_orchestration", "collaborative_decision"})
MEMBER_ONLY_SKILLS = frozenset({"financial_audit", "data_visualization"})

def assert_membership_for_mode(user: UserContext, mode: str) -> None:
    canonical = normalize_execution_mode(mode)
    if canonical in MEMBER_ONLY_MODES and not user.is_member:
        raise MembershipRequiredError("该执行模式需开通会员")

def assert_membership_for_skill(user: UserContext, skill: str | None) -> None:
    if skill and skill in MEMBER_ONLY_SKILLS and not user.is_member:
        raise MembershipRequiredError("该技能需开通会员")

def assert_membership_for_expert(user: UserContext, expert_id: str | None) -> None:
    # finance_reviewer → plan_execute, finance_review_board → multi_agent
    ...
```

### 8.3 orchestrator.py 改造

```python
def _select_mode(self, user_input: str, mode: str, *, user: UserContext) -> str:
    canonical = normalize_execution_mode(mode)
    if canonical != "adaptive":
        assert_membership_for_mode(user, canonical)
        return canonical

    # adaptive routing
    if not user.is_member:
        # 普通用户：Auto 固定走 ReAct，不做关键词升级
        return "reasoning_action"

    # 会员：完整智能路由（现有逻辑）
    ...
```

### 8.4 chat.py 改造

在 `orchestrator.stream` 调用前：

```python
from app.services.membership_gate import (
    assert_membership_for_mode,
    assert_membership_for_skill,
    assert_membership_for_expert,
)
from app.services.quota_service import check_quota

# 解析 runtime_policy 后
resolved = resolve(...)
assert_membership_for_mode(user, resolved.mode)
assert_membership_for_skill(user, resolved.skill)
assert_membership_for_expert(user, resolved.expert_id)
await check_quota("daily_message", user.user_id, user.user_type)

try:
    async for event in orchestrator.stream(..., user=user):
        ...
except MembershipRequiredError as e:
    await websocket.send_json({
        "type": "error",
        "code": "MEMBERSHIP_REQUIRED",
        "message": str(e),
    })
```

### 8.5 quota_service.py

```python
async def check_quota(action: str, user_id: int, user_type: str, db: AsyncSession) -> None:
    """
    action ∈ create_session | upload_document | daily_message
    超限 raise QuotaExceededError(quota_key, message)
    """
```

**计数来源**：

| action | 计数方式 |
|--------|----------|
| create_session | `COUNT chat_sessions WHERE user_id AND deleted_at IS NULL` |
| upload_document | `COUNT knowledge_documents WHERE user_id AND visibility=private` |
| daily_message | Redis `quota:msg:{user_id}:{date}` 或 MySQL 日计数表 |

Phase 3 可先用 MySQL 计数；Redis 为 P2 优化。

### 8.6 RAG tenant_filter 扩展

```python
def build_retrieval_filter(user_id: int, user_type: str) -> dict:
    private = {"user_id": user_id, "visibility": "private"}
    if user_type == "member":  # 且 is_member 已在 auth 层校验
        return {"$or": [private, {"visibility": "member"}]}
    return private
```

### 8.7 会员过期降级（已有，保持）

`auth.py` → `_normalize_membership()`：登录 / get_current_user 时 `member` 且过期 → 写回 `regular`。

### 8.8 运维脚本

| 脚本 | 用途 |
|------|------|
| `scripts/grant_membership.py` | `python -m scripts.grant_membership --user demo --days 365` |
| `scripts/seed_member_knowledge.py` | 灌库 visibility=member |
| `scripts/generate_redeem_codes.py` | 批量生成兑换码 |

---

## 9. 前端实现规范

### 9.1 新增 / 改造文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `stores/membership.ts` | 新增 | status、quota、fetch、refresh |
| `components/ui/UpgradePrompt.vue` | 新增 | 升级弹窗 |
| `components/ui/LockedFeature.vue` | 新增 | 锁定遮罩 + 文案 |
| `views/MembershipView.vue` | 改造 | 完整会员中心 |
| `views/MembershipRedeemView.vue` | 新增 | 兑换码（P2 可合并） |
| `views/ChatView.vue` | 改造 | 模式过滤、错误处理 |
| `views/SkillsView.vue` | 改造 | 会员标签、点击拦截 |
| `views/KnowledgeView.vue` | 改造 | 分区 Tab、配额 |
| `api/client.ts` | 改造 | membership API |
| `api/websocket.ts` | 改造 | 监听 MEMBERSHIP_REQUIRED |
| `stores/settings.ts` | 改造 | 非会员强制 adaptive |

### 9.2 membership store

```typescript
interface MembershipState {
  isMember: boolean
  isTrial: boolean
  expiresAt: string | null
  daysRemaining: number | null
  quota: QuotaSnapshot | null
  plans: Plan[]
  upgradeUrl: string | null
  loaded: boolean
}

async function refresh(): Promise<void> {
  const [status, quota] = await Promise.all([
    fetchMembershipStatus(),
    fetchMembershipQuota(),
  ])
  // 同步到 authStore（isMember 以 status 为准）
}
```

登录成功后、`/membership` 进入时、兑换成功后调用 `refresh()`。

### 9.3 ChatView 模式 computed

```typescript
const visibleModeOptions = computed(() => {
  if (authStore.isMember) return executionModeOptions
  return executionModeOptions.filter(o => o.value === 'adaptive')
})

watch(() => authStore.isMember, (member) => {
  if (!member && settingsStore.selectedMode !== 'adaptive') {
    settingsStore.selectedMode = 'adaptive'
  }
})
```

### 9.4 WS 错误处理

```typescript
// websocket.ts 或 chat store
if (msg.type === 'error' && msg.code === 'MEMBERSHIP_REQUIRED') {
  emit('membership-required', msg)
}
// ChatView 监听 → UpgradePrompt.open(msg.message)
```

---

## 10. 安全要求

| 项 | 要求 |
|----|------|
| user_type 来源 | **仅** JWT/DB，禁止 WS body 传入 |
| Webhook | HMAC-SHA256 签名校验 + 幂等 |
| 兑换码 | 大小写归一； brute-force 限流 5 次/分钟/IP |
| 会员库删除 | API 禁止用户删除 visibility=member 文档 |
| API Key | 会员个人 Key AES-256-GCM 加密（Phase 4） |
| 审计 | membership.activated / membership.redeemed / quota.exceeded 写 audit_logs |

---

## 11. 实施分期

### Phase 3A — 门控 MVP（1～1.5 周）

| ID | 任务 |
|----|------|
| P3A-01 | membership_gate.py + orchestrator 改造 |
| P3A-02 | chat.py WS 门控 + WS error 事件 |
| P3A-03 | skills API membership_required 元数据 + execute 门控 |
| P3A-04 | 前端模式过滤 + UpgradePrompt |
| P3A-05 | GET /api/membership/status |

**验收**：用例 TC-01～TC-06 通过。

### Phase 3B — 配额与 RAG（1 周）

| ID | 任务 |
|----|------|
| P3B-01 | quota_service + GET /api/membership/quota |
| P3B-02 | create_session / upload 配额钩子 |
| P3B-03 | tenant_filter member 分支 |
| P3B-04 | 知识库分区 UI + 配额展示 |

**验收**：用例 TC-07～TC-10 通过。

### Phase 3C — 开通与会员中心（1 周）

| ID | 任务 |
|----|------|
| P3C-01 | membership_orders / membership_codes 表 |
| P3C-02 | POST /api/membership/webhook |
| P3C-03 | POST /api/membership/redeem |
| P3C-04 | MembershipView 完整版 |
| P3C-05 | 注册试用钩子（可配置） |
| P3C-06 | grant_membership / seed_member_knowledge 脚本 |

**验收**：用例 TC-11～TC-15 通过。

### Phase 4 — 增强（可选）

- JWT Refresh + 黑名单
- GET /api/membership/orders
- 到期前 7 天邮件/站内提醒
- Redis 日消息计数
- API Key 加密存储

---

## 12. 验收标准与测试用例

### 12.1 功能验收清单

- [ ] 普通用户 UI 仅 Auto；WS 发 Plan 返回 MEMBERSHIP_REQUIRED
- [ ] 普通用户 Auto +「审计报告」不升 Plan，走 ReAct
- [ ] 会员 Auto +「审计报告」升 Plan
- [ ] 会员手动 Plan 模式正常 STEP 事件流
- [ ] financial_audit 普通用户 403，会员 200
- [ ] 普通用户 RAG 不含 member 库；会员含
- [ ] 会话数超限 429；会员上限更高
- [ ] Webhook 幂等；重复 order_id 不重复延期
- [ ] 兑换码一次性；过期码失败
- [ ] 会员过期登录后降级；Plan 403
- [ ] 注册试用（若开启）7 天后自动降级

### 12.2 测试用例

| ID | 前置 | 操作 | 期望 |
|----|------|------|------|
| TC-01 | test_regular | ChatView 模式选项 | 仅 Auto |
| TC-02 | test_regular | WS mode=task_orchestration | error MEMBERSHIP_REQUIRED |
| TC-03 | test_regular | 输入「请做财务审计」Auto | reasoning_action，无 STEP 事件 |
| TC-04 | test_member | 同上 | task_orchestration 或 STEP 事件 |
| TC-05 | test_regular | POST skills/financial_audit/execute | 403 |
| TC-06 | test_member | Plan 模式复杂任务 | 正常完成 |
| TC-07 | regular 已有 20 session | POST /api/sessions | 429 QUOTA_EXCEEDED |
| TC-08 | regular 已有 10 docs | POST upload | 429 |
| TC-09 | test_member | RAG 查询 | 结果含 member 库 chunk |
| TC-10 | test_regular | 同上 | 仅 private chunk |
| TC-11 | — | Webhook 月卡 | user 变 member，expires +30d |
| TC-12 | — | 重复 Webhook 同 order_id | 200，expires 不变 |
| TC-13 | regular | POST redeem 有效码 | member，expires 正确 |
| TC-14 | — | redeem 已用码 | 400 REDEEM_CODE_USED |
| TC-15 | expired_member 登录 | GET /api/auth/me | user_type=regular |

### 12.3 性能与稳定性

| 指标 | 目标 |
|------|------|
| membership_gate 延迟 | < 5ms（纯内存判断） |
| quota 查询 | < 50ms（MySQL 计数） |
| Webhook 处理 | < 200ms |

---

## 13. 监控与指标（P2）

| 指标 | 说明 |
|------|------|
| `membership_gate_blocked_total` | 按 mode/skill 分维度 |
| `quota_exceeded_total` | 按 quota 类型 |
| `membership_activated_total` | 按 source：webhook/redeem/trial |
| `upgrade_prompt_shown_total` | 前端埋点 |
| `trial_to_paid_conversion` | 试用转付费率 |

---

## 14. 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `MEMBERSHIP_WEBHOOK_SECRET` | 生产必填 | Webhook HMAC 密钥 |
| `MEMBERSHIP_UPGRADE_URL` | 否 | 外链支付页模板，含 `{user_id}` |
| `MEMBERSHIP_TRIAL_ENABLED` | 否 | 覆盖 system_settings 试用开关 |

---

## 15. 相关文档与功能 ID 映射

| PRD 章节 | 设计文档 | 功能 ID |
|----------|----------|---------|
| §6 接口 | 04-权限 | M-01～M-07 |
| §8 后端 | 09-路线图 Phase 3 | G-01～G-06, C-07～C-08, K-05～K-06 |
| §9 前端 | 11-页面清单 | F-04, F-07～F-15, F-23～F-24 |
| §7 数据模型 | 05-数据模型 | B-11, B-12 |

---

## 16. 附录 A — 会员专享技能与专家映射

| 资源 | default_mode | 普通用户 | 会员 |
|------|--------------|----------|------|
| skill: financial_audit | — | ✗ | ✓ |
| skill: data_visualization | — | ✗ | ✓ |
| expert: finance_reviewer | task_orchestration | ✗ | ✓ |
| expert: finance_review_board | collaborative_decision | ✗ | ✓ |
| expert: document_insight | reasoning_action | ✓ | ✓ |
| expert: report_analyst | reasoning_action | ✓ | ✓ |

## 17. 附录 B — Webhook 签名算法

```
payload = request.body (raw bytes)
signature = HMAC-SHA256(MEMBERSHIP_WEBHOOK_SECRET, payload).hexdigest()
header X-Webhook-Signature = f"sha256={signature}"
```

服务端：常量时间比较；拒绝 timestamp 偏差 > 5 分钟（若 body 含 timestamp 字段）。

## 18. 附录 C — 兑换码生成规则

- 格式：`PREFIX-RANDOM`（如 `FIN-A1B2C3D4`）
- 字符集：大写字母 + 数字，排除易混淆 0/O/I/1
- 默认 `max_uses=1`，`duration_days=365`

---

**文档维护**：实现过程中若 API 字段或配额默认值变更，须同步更新本 PRD 版本号与变更记录。

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-08-11 | 初版完整 PRD |

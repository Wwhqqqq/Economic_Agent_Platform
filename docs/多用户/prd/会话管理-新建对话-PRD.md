# PRD — 会话管理：新建对话与空会话复用

> **版本**：1.0  
> **日期**：2026-08-15  
> **状态**：待实现  
> **优先级**：P0（线上回归）  
> **关联文档**：[03 — 身份认证与会话](../03-身份认证与会话/README.md)、[11 — 页面与功能清单](../11-页面与功能清单/README.md)

---

## 1. 背景与问题

### 1.1 现象

用户在有历史记录的对话中点击「新建对话」后，新发送的问题仍追加到**最近一次有记录的对话**下，侧边栏不出现新的对话条目，表现为「新建对话无效」。

### 1.2 根因定位

| 层级 | 文件 | 问题 |
|------|------|------|
| 前端 Store | `frontend/src/stores/chat.ts` L190–198 | `isCurrentSessionEmpty()` **仅判断** `messages.value.length === 0`，未考虑服务端 `message_count` |
| 前端 Store | 同上 | 用户点击「新建对话」时若本地 messages 为空但 `sessionId` 仍指向**服务端有历史**的会话 → **early return**，不调用 API，**不换 sessionId** |
| 前端 App | `frontend/src/App.vue` L189–191 | `createSession()` 未 `await newSession()`，存在竞态 |
| 后端 API | `backend/app/api/chat.py` L308–312 | `POST /api/sessions` 无条件复用任意空会话，未区分「用户主动新建」与「系统初始化」，也未排除当前会话 |

### 1.3 典型复现路径

1. 用户在侧边栏选中一条有历史记录的对话（或刚聊完一轮）  
2. 本地 `messages` 因切换加载时序、刷新后状态等原因暂时为空，或服务端有记录但 UI 已清空  
3. 点击「新建对话」→ 命中 early return → `sessionId` 不变  
4. 发送新问题 → WebSocket 仍连旧 session → 消息写入旧对话  

---

## 2. 目标

1. **用户点击「新建对话」**：若当前会话**已有内容**（本地或服务端任一非空），必须切换到**新的会话 ID**，后续消息不得写入旧会话。  
2. **空会话去重**：若当前会话**真正为空**（本地 messages 为空 **且** 服务端 message_count === 0），再次点击「新建对话」**不创建重复空会话**，继续复用当前 sessionId。  
3. **系统初始化**（登录后、删除当前会话后）：仍优先复用最新空会话，避免数据库堆积空白记录。  
4. **历史列表**：仅展示 `message_count > 0` 的会话（保持现有行为）。  

---

## 3. 术语

| 术语 | 定义 |
|------|------|
| 真正空会话 | 本地 `messages.length === 0` 且服务端该 session 的 `message_count === 0` |
| 用户主动新建 | 用户点击侧边栏「新建对话」按钮 |
| 系统初始化 | 登录成功、删除当前会话后自动调用 `newSession()` |

---

## 4. 功能规格

### 4.1 用户点击「新建对话」

```
IF 当前会话为「真正空会话」
  THEN 保持当前 sessionId，清空 UI，重连 WebSocket（静默）
ELSE
  THEN 调用 POST /api/sessions { force_new: true, exclude_session_id: 当前ID }
       切换到返回的新 sessionId，清空 UI，重连 WebSocket
```

### 4.2 系统初始化 newSession()

```
IF 当前 sessionId 存在且为「真正空会话」
  THEN 复用当前 sessionId（early return）
ELSE IF 无 sessionId 或当前非空
  THEN 调用 POST /api/sessions（默认 force_new: false）
       后端复用最新空会话或创建新 UUID
```

### 4.3 后端 POST /api/sessions

**请求体扩展：**

```json
{
  "title": "新对话",
  "force_new": false,
  "exclude_session_id": "optional-uuid"
}
```

**逻辑：**

| force_new | exclude_session_id | 行为 |
|-----------|-------------------|------|
| `false` | 忽略 | 复用用户最新空会话；无则创建新 UUID（现有初始化逻辑） |
| `true` | 当前 sessionId | 若 excluded 会话 message_count === 0 → **直接返回该会话**（真正空，不重复创建） |
| `true` | 当前 sessionId | 若 excluded 会话 message_count > 0 → **排除该 ID**，复用其他空会话；无则 **强制 create 新 UUID** |

### 4.4 会话列表与右键菜单（保持不变）

- 列表：仅 `message_count > 0`  
- 右键：导出 Markdown、删除（软删除整段会话）  
- 清空对话：`POST /sessions/{id}/clear`（只清消息，不删会话）  

---

## 5. 前端实现要点

### 5.1 `getCurrentSessionServerMessageCount()`

- 从 `sessions` 列表查找当前 `sessionId` 的 `message_count`  
- 不在列表中（空会话未展示）→ 视为 0  

### 5.2 `isCurrentSessionEmpty()`

```ts
messages.value.length === 0 && getCurrentSessionServerMessageCount() === 0
```

### 5.3 `newSession(options?: { userInitiated?: boolean })`

- `userInitiated: true` ← `App.vue` 的「新建对话」按钮  
- 有内容时必须 `force_new: true` + `exclude_session_id`  
- `createSession()` 必须 `await chatStore.newSession({ userInitiated: true })`  

### 5.4 切换会话后

- `switchSession` 加载完消息后，服务端计数与本地一致  
- `loadSessions()` / `done` 事件后刷新 `sessions` 列表，保证 server count 准确  

---

## 6. 接口变更

### POST /api/sessions

**Request**

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| title | string | "新对话" | 会话标题 |
| force_new | boolean | false | 用户主动新建时为 true |
| exclude_session_id | string \| null | null | 排除复用的会话 ID |

**Response**（不变）

```json
{
  "session_id": "uuid",
  "title": "新对话",
  "created_at": "ISO8601"
}
```

---

## 7. 验收标准

| # | 场景 | 预期 |
|---|------|------|
| AC-1 | 在有 3 条以上消息的对话中点击「新建对话」 | 主区清空；发送新问题后侧边栏出现**新条目**或旧条目 message_count 不变、新条目增加 |
| AC-2 | 空会话连点两次「新建对话」 | 不产生第二个空 sessionId；侧边栏仍无空会话条目 |
| AC-3 | 空会话发一条消息后点「新建对话」 | 切换到新 sessionId；旧对话保留在侧边栏 |
| AC-4 | 登录后首次进入 | 自动获得可用 sessionId，WebSocket 连接成功 |
| AC-5 | 选中历史对话后立即点「新建对话」 | 即使 messages 尚在加载，也不应把新消息写入该历史对话 |
| AC-6 | 删除当前对话后 | 自动进入新的可用空会话 |

---

## 8. 非目标

- 不改变清空 / 删除 / 导出已有交互  
- 不改变列表只展示有记录会话的策略  
- 不引入 sessionId 本地持久化（刷新后仍走初始化逻辑）  

---

## 9. 改动文件清单

| 文件 | 改动 |
|------|------|
| `docs/多用户/prd/会话管理-新建对话-PRD.md` | 本文档 |
| `backend/app/services/chat_session_service.py` | `get_message_count`、`find_reusable_empty_session(exclude_ids)` |
| `backend/app/api/chat.py` | `SessionCreateRequest` 扩展、`create_session` 分支逻辑 |
| `frontend/src/api/client.ts` | `createSession(title, options?)` |
| `frontend/src/stores/chat.ts` | server count、双模式 `newSession` |
| `frontend/src/App.vue` | `await newSession({ userInitiated: true })` |

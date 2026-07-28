# 08 — 高并发与性能

## 1. 负载特征

（LLM 仍为主瓶颈；MySQL 压力可控，同前。）

## 2. 按用户类型的限流

| 限流项 | 普通用户 | 会员用户 |
|--------|----------|----------|
| POST /auth/login | 5/min/IP | 同 |
| WS message | 30/min/user | 120/min/user |
| knowledge upload | 5/hour | 30/hour |
| 并发 LLM 请求 | 1 | 3 |

实现：Redis sliding window，key 含 `user_id` 与 `user_type`。

## 3. MySQL / Redis / WS

（连接池、消息批量写、无状态 WS，同前。）

**会员过期降级**：可在 `get_current_user` 查库，高并发下考虑 Redis 缓存 `user:{id}:type` TTL 5min，过期/Webhook 时 invalidate。

## 4. RAG 检索

会员用户 RAG 多一路 member 库，略增 Chroma query 复杂度；仍应先 filter 再 RRF，性能影响可忽略。

## 5. 水平扩展

（无状态 API、共享 MySQL/Redis，同前。）

## 6. 相关文档

- [04 — 权限与租户隔离](../04-权限与租户隔离/README.md)

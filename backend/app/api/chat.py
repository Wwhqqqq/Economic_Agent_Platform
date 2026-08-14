"""
WebSocket 聊天路由 — 核心交互接口
"""
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.base import AgentConfig
from app.agent.orchestrator import orchestrator
from app.core.catalog import normalize_execution_mode
from app.core.config import config as app_config
from app.core.database import get_db, session_scope
from app.core.connection_context import ConnectionContext, set_connection_context
from app.core.runtime_policy import MessageContext, apply_to_session, resolve
from app.core.session_context import (
    clear_session_expert,
    clear_session_skill,
    get_session_context,
    set_session_expert,
    set_session_skill,
)
from app.core.slash_parser import parse_slash_command
from app.skills.registry import skill_registry
from app.memory.manager import memory_manager
from app.schemas.user_context import UserContext
from app.services.auth import AUTH_ENABLED, get_current_user, verify_token, get_user_by_id, user_to_context
from app.services.attachment_service import resolve_chat_attachments
from app.services.chat_session_service import chat_session_service
from app.services.membership_gate import (
    MembershipRequiredError,
    assert_membership_for_resolved,
)
from app.services.quota_service import QuotaExceededError, check_quota
from langchain_core.messages import AIMessage, HumanMessage

router = APIRouter()


class SessionRenameRequest(BaseModel):
    title: str


class SessionCreateRequest(BaseModel):
    title: str = "新对话"


async def _ws_authenticate(websocket: WebSocket, session_id: str) -> UserContext:
    if not AUTH_ENABLED:
        return UserContext.anonymous()

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Unauthorized")
        raise WebSocketDisconnect(code=4401)

    payload = verify_token(token)
    if not payload:
        await websocket.close(code=4401, reason="Unauthorized")
        raise WebSocketDisconnect(code=4401)

    user_id = int(payload["sub"])
    async with session_scope() as db:
        session = await chat_session_service.get_owned_session(db, session_id, user_id)
        if not session:
            await websocket.close(code=4403, reason="Forbidden")
            raise WebSocketDisconnect(code=4403)
        db_user = await get_user_by_id(db, user_id)
        if not db_user or db_user.status != "active":
            await websocket.close(code=4401, reason="Unauthorized")
            raise WebSocketDisconnect(code=4401)
        return user_to_context(db_user)


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    try:
        user = await _ws_authenticate(websocket, session_id)
    except WebSocketDisconnect:
        return

    await websocket.accept()
    await websocket.send_json({
        "type": "connected",
        "data": {"session_id": session_id, "user_id": user.user_id},
    })

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") != "message":
                continue

            user_input = data.get("input", "")
            attachments = data.get("attachments") or []
            if (
                not user_input.strip()
                and not attachments
                and not data.get("clear_skill")
                and not data.get("clear_expert")
            ):
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Empty input"},
                })
                continue

            session_ctx = get_session_context(session_id)

            if data.get("clear_expert"):
                clear_session_expert(session_id)
            if data.get("expert_id"):
                set_session_expert(session_id, data.get("expert_id"))
            if data.get("clear_skill"):
                clear_session_skill(session_id)

            clear_only = (
                not user_input.strip()
                and not attachments
                and (data.get("clear_skill") or data.get("clear_expert"))
            )
            if clear_only:
                from app.core.session_context import session_context_to_public
                await websocket.send_json({
                    "type": "context_updated",
                    "data": session_context_to_public(session_id),
                })
                continue

            parsed_skill, parsed_message = parse_slash_command(user_input)
            user_message = parsed_message if parsed_skill else user_input
            if not user_message.strip() and attachments:
                user_message = "请分析附件。"

            if parsed_skill:
                if not skill_registry.get(parsed_skill):
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"未找到技能 `{parsed_skill}`"},
                    })
                    continue
                user_input = user_message
                if not user_input.strip() and not attachments:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "请在 `/技能名` 后补充任务描述"},
                    })
                    continue

            user_input = user_message

            msg_ctx = MessageContext(
                parsed_slash_skill=parsed_skill,
                skill=data.get("skill"),
                mode=data.get("mode"),
                expert_id=data.get("expert_id"),
                skill_invocation=data.get("skill_invocation"),
                clear_skill=bool(data.get("clear_skill")),
                clear_expert=bool(data.get("clear_expert")),
                user_input=user_input,
            )

            resolved = resolve(session_ctx, msg_ctx)
            apply_to_session(session_ctx, resolved)

            mode = normalize_execution_mode(resolved.mode)

            try:
                assert_membership_for_resolved(
                    user,
                    mode=mode,
                    skill=resolved.skill or parsed_skill,
                    expert_id=resolved.expert_id or data.get("expert_id"),
                    requested_mode=data.get("mode"),
                )
            except MembershipRequiredError as exc:
                await websocket.send_json({
                    "type": "error",
                    "code": "MEMBERSHIP_REQUIRED",
                    "data": {"message": exc.message, "upgrade_url": "/membership"},
                })
                continue

            if user.user_id:
                async with session_scope() as db:
                    try:
                        await check_quota(db, "daily_message", user.user_id, user.user_type)
                    except QuotaExceededError as exc:
                        await websocket.send_json({
                            "type": "error",
                            "code": "QUOTA_EXCEEDED",
                            "data": {"message": exc.message, "quota": exc.quota},
                        })
                        continue

            set_connection_context(
                ConnectionContext(
                    user_id=user.user_id,
                    user_type=user.user_type,
                    session_id=session_id,
                    active_skill=resolved.skill,
                )
            )

            provider = data.get("provider") or app_config.agent.default_provider
            resolved_attachments = attachments if isinstance(attachments, list) else []
            if resolved_attachments and user.user_id:
                async with session_scope() as db:
                    resolved_attachments = await resolve_chat_attachments(
                        db, user.user_id, resolved_attachments
                    )

            max_iterations = app_config.agent.max_iterations
            if resolved_attachments:
                max_iterations = min(max_iterations, 5)

            agent_config = AgentConfig(
                session_id=session_id,
                user_id=user.user_id if user.user_id else None,
                user_type=user.user_type,
                active_skill=resolved.skill,
                expert_id=resolved.expert_id,
                skill_invocation=resolved.skill_invocation,
                context_strategy=resolved.context_strategy,
                provider=provider,
                model=data.get("model"),
                temperature=data.get("temperature", 0.7),
                streaming=True,
                system_prompt=resolved.system_prompt,
                engine=resolved.engine,
                team_protocol=resolved.team_protocol,
                team_class=resolved.team_class,
                attachments=resolved_attachments,
                max_iterations=max_iterations,
            )

            timeout = app_config.agent.timeout_seconds

            try:
                async def _stream():
                    async for event in orchestrator.stream(user_input, agent_config, mode, user=user):
                        await websocket.send_json({
                            "type": event.type.value,
                            "data": event.data,
                            "metadata": event.metadata,
                        })

                await asyncio.wait_for(_stream(), timeout=timeout)
            except MembershipRequiredError as exc:
                await websocket.send_json({
                    "type": "error",
                    "code": "MEMBERSHIP_REQUIRED",
                    "data": {"message": exc.message, "upgrade_url": "/membership"},
                })
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"执行超时（>{timeout}s），请简化任务后重试"},
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": str(e)},
                })
            finally:
                await websocket.send_json({"type": "done", "data": {}})

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {session_id}")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)},
            })
        except Exception:
            pass


@router.post("/api/sessions")
async def create_session(
    req: SessionCreateRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if AUTH_ENABLED and user.user_id == 0:
        raise HTTPException(status_code=401, detail="未登录")
    uid = user.user_id if user.user_id else 0
    if uid == 0:
        import uuid
        sid = str(uuid.uuid4())
        return {
            "session_id": sid,
            "title": req.title,
            "created_at": None,
            "note": "anonymous_mode",
        }
    try:
        await check_quota(db, "create_session", uid, user.user_type)
    except QuotaExceededError as exc:
        from app.services.quota_service import quota_http_exception
        raise quota_http_exception(exc) from exc
    reusable = await chat_session_service.find_reusable_empty_session(db, uid)
    if reusable:
        session = reusable
    else:
        session = await chat_session_service.create_session(db, uid, req.title)
    return {
        "session_id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.get("/api/sessions")
async def list_sessions(
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if AUTH_ENABLED and user.user_id:
        sessions = await chat_session_service.list_sessions(db, user.user_id)
        return {"sessions": sessions}
    return {"sessions": memory_manager.short_term.list_sessions()}


@router.post("/api/sessions/{session_id}/clear")
async def clear_session_messages(
    session_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """仅清空会话消息，保留会话本身（用于「清空对话」）。"""
    if AUTH_ENABLED and user.user_id:
        owned = await chat_session_service.get_owned_session(db, session_id, user.user_id)
        if not owned:
            raise HTTPException(status_code=403, detail="无权访问该会话")
        await chat_session_service.delete_messages(db, session_id, user.user_id)
        result = await memory_manager.clear_session_all(session_id, user_id=user.user_id)
        return {"status": "cleared", **result}
    result = await memory_manager.clear_session_all(session_id)
    return {"status": "cleared", **result}


@router.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """永久删除会话（右键删除）。"""
    if AUTH_ENABLED and user.user_id:
        owned = await chat_session_service.get_owned_session(db, session_id, user.user_id)
        if not owned:
            raise HTTPException(status_code=403, detail="无权访问该会话")
        await chat_session_service.delete_messages(db, session_id, user.user_id)
        await chat_session_service.soft_delete_session(db, session_id, user.user_id)
        result = await memory_manager.clear_session_all(session_id, user_id=user.user_id)
        return {"status": "deleted", **result}
    result = await memory_manager.clear_session_all(session_id)
    return {"status": "deleted", **result}


@router.patch("/api/sessions/{session_id}")
async def rename_session(
    session_id: str,
    req: SessionRenameRequest,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if AUTH_ENABLED and user.user_id:
        ok = await chat_session_service.rename_session(db, session_id, user.user_id, req.title)
        if not ok:
            raise HTTPException(status_code=404, detail="会话不存在")
        return {"status": "updated", "title": req.title}
    ok = memory_manager.short_term.rename(session_id, req.title)
    if not ok:
        return {"status": "not_found"}
    return {"status": "updated", "title": req.title}


@router.get("/api/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if AUTH_ENABLED and user.user_id:
        owned = await chat_session_service.get_owned_session(db, session_id, user.user_id)
        if not owned:
            raise HTTPException(status_code=403, detail="无权访问该会话")
        messages = await chat_session_service.get_messages(db, session_id, user.user_id)
        return {"session_id": session_id, "messages": messages}

    messages = memory_manager.short_term.get_messages(session_id)
    formatted = []
    for m in messages:
        if isinstance(m, HumanMessage):
            role = "user"
        elif isinstance(m, AIMessage):
            role = "assistant"
        else:
            role = "system"
        formatted.append({"role": role, "content": m.content})
    return {"session_id": session_id, "messages": formatted}

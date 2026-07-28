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
from app.memory.manager import memory_manager
from app.schemas.user_context import UserContext
from app.services.auth import AUTH_ENABLED, get_current_user, verify_token
from app.services.chat_session_service import chat_session_service
from app.skills.registry import skill_registry
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

    return UserContext(
        user_id=user_id,
        username=payload.get("username", ""),
        user_type=payload.get("user_type", "regular"),
    )


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
            if not user_input.strip():
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Empty input"},
                })
                continue

            skill_name = data.get("skill")
            if skill_name:
                skill_registry.activate(skill_name)
            else:
                skill_registry.deactivate()

            provider = data.get("provider") or app_config.agent.default_provider
            agent_config = AgentConfig(
                session_id=session_id,
                user_id=user.user_id if user.user_id else None,
                provider=provider,
                model=data.get("model"),
                temperature=data.get("temperature", 0.7),
                streaming=True,
                system_prompt=None,
            )

            mode = normalize_execution_mode(data.get("mode", "adaptive"))
            timeout = app_config.agent.timeout_seconds

            try:
                async def _stream():
                    async for event in orchestrator.stream(user_input, agent_config, mode):
                        await websocket.send_json({
                            "type": event.type.value,
                            "data": event.data,
                            "metadata": event.metadata,
                        })

                await asyncio.wait_for(_stream(), timeout=timeout)
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"执行超时（>{timeout}s），请简化任务后重试"},
                })
                await websocket.send_json({"type": "done", "data": {}})
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": str(e)},
                })

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


@router.delete("/api/sessions/{session_id}")
async def clear_session(
    session_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if AUTH_ENABLED and user.user_id:
        owned = await chat_session_service.get_owned_session(db, session_id, user.user_id)
        if not owned:
            raise HTTPException(status_code=403, detail="无权访问该会话")
        await chat_session_service.delete_messages(db, session_id, user.user_id)
        result = await memory_manager.clear_session_all(session_id, user_id=user.user_id)
        return {"status": "cleared", **result}
    result = await memory_manager.clear_session_all(session_id)
    return {"status": "cleared", **result}


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

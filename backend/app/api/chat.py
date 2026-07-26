"""
WebSocket 聊天路由 — 核心交互接口
"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.agent.base import AgentConfig
from app.agent.orchestrator import orchestrator
from app.core.catalog import normalize_execution_mode
from app.core.config import config as app_config
from app.skills.registry import skill_registry

router = APIRouter()


class SessionRenameRequest(BaseModel):
    title: str


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    await websocket.send_json({
        "type": "connected",
        "data": {"session_id": session_id},
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


@router.delete("/api/sessions/{session_id}")
async def clear_session(session_id: str):
    from app.memory.manager import memory_manager
    result = await memory_manager.clear_session_all(session_id)
    return {"status": "cleared", **result}


@router.get("/api/sessions")
async def list_sessions():
    from app.memory.manager import memory_manager
    return {"sessions": memory_manager.short_term.list_sessions()}


@router.patch("/api/sessions/{session_id}")
async def rename_session(session_id: str, req: SessionRenameRequest):
    from app.memory.manager import memory_manager
    ok = memory_manager.short_term.rename(session_id, req.title)
    if not ok:
        return {"status": "not_found"}
    return {"status": "updated", "title": req.title}


@router.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    from app.memory.manager import memory_manager
    from langchain_core.messages import HumanMessage, AIMessage
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

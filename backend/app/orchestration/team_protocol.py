from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, AsyncIterator

import yaml

from app.agent.base import AgentConfig, AgentEvent, AgentEventType, AgentResponse
from app.agent.runtime import (
    collect_prompt_tool_response,
    create_llm,
    message_content,
    normalize_agent_config,
    run_prompt_tool_loop,
)
from app.tools.registry import tool_registry

PROTOCOLS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "experts",
    "_protocols",
)


def _load_protocol(protocol_id: str) -> dict:
    path = Path(PROTOCOLS_ROOT) / f"{protocol_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Team protocol not found: {protocol_id}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class TeamProtocolEngine:
    """Config-driven multi-role team execution (debate_v1, etc.)."""

    name = "team_protocol_engine"

    async def stream(
        self,
        user_input: str,
        config: AgentConfig | None = None,
        *,
        protocol_id: str = "debate_v1",
    ) -> AsyncIterator[AgentEvent]:
        config = normalize_agent_config(config)
        protocol = _load_protocol(protocol_id)
        roles = {r["id"]: r for r in protocol.get("roles", [])}
        outputs: dict[str, str] = {}

        yield AgentEvent(
            type=AgentEventType.START,
            data={"protocol": protocol_id, "team": protocol.get("display", {}).get("name", protocol_id)},
        )

        for step in protocol.get("flow", []):
            role_id = step.get("role", "")
            role = roles.get(role_id, {})
            persona = role.get("persona", f"You are role {role_id}.")
            tool_names = role.get("tools") or []
            tools = tool_registry.to_langchain_tools() if tool_names else []
            if tool_names:
                tools = [t for t in tools if getattr(t, "name", "") in tool_names]

            context_parts = [persona, f"\n## User Task\n{user_input}"]
            if step.get("input") == "previous_outputs" and outputs:
                context_parts.append("\n## Previous Role Outputs")
                for rid, text in outputs.items():
                    context_parts.append(f"### {rid}\n{text[:2000]}")
            elif step.get("input") == "all_previous" and outputs:
                context_parts.append("\n## All Previous Outputs")
                for rid, text in outputs.items():
                    context_parts.append(f"### {rid}\n{text[:2000]}")

            prompt = "\n".join(context_parts)
            yield AgentEvent(
                type=AgentEventType.THINKING,
                data={"role": role_id, "message": f"{role.get('display_name', role_id)} 正在分析…"},
                metadata={"role": role_id},
            )

            role_output = ""
            tool_calls: list[dict] = []
            async for event in run_prompt_tool_loop(
                prompt,
                temperature=float(role.get("temperature", 0.4)),
                tools=tools,
                max_iterations=int(role.get("max_iterations", 5)),
            ):
                if isinstance(event, AgentEvent):
                    if event.type == AgentEventType.TOKEN:
                        role_output += event.data.get("content", "")
                        yield AgentEvent(
                            type=AgentEventType.TOKEN,
                            data={"content": event.data.get("content", ""), "role": role_id},
                            metadata={"role": role_id},
                        )
                elif isinstance(event, tuple):
                    role_output, tool_calls = event

            outputs[role_id] = role_output
            yield AgentEvent(
                type=AgentEventType.MESSAGE,
                data={
                    "role": role_id,
                    "display_name": role.get("display_name", role_id),
                    "content": role_output,
                    "tool_calls": tool_calls,
                },
                metadata={"role": role_id},
            )

        yield AgentEvent(type=AgentEventType.DONE, data={"outputs": list(outputs.keys())})

    async def invoke(
        self,
        user_input: str,
        config: AgentConfig | None = None,
        *,
        protocol_id: str = "debate_v1",
    ) -> AgentResponse:
        final = ""
        tool_calls: list[dict] = []
        async for event in self.stream(user_input, config, protocol_id=protocol_id):
            if event.type == AgentEventType.MESSAGE:
                final += f"\n\n## {event.data.get('display_name', event.data.get('role', ''))}\n"
                final += event.data.get("content", "")
                tool_calls.extend(event.data.get("tool_calls") or [])
        return AgentResponse(output=final.strip(), tool_calls=tool_calls)

"""
Agent 运行时共享模块

统一 DeepSeek 配置、技能 Prompt 注入、工具筛选与 ReAct 执行循环。
"""
from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.base import AgentConfig, AgentEvent, AgentEventType, AgentResponse
from app.core.config import config as app_config
from app.llm.factory import LLMFactory
from app.memory.manager import memory_manager
from app.skills.registry import skill_registry
from app.tools.registry import tool_registry

FIXED_LLM_PROVIDER = "deepseek"  # fallback default only
CONTEXT_LOAD_TIMEOUT = 10.0


def extract_token_usage(response: AIMessage) -> int:
    """Extract token usage from LangChain AIMessage metadata."""
    total = 0
    meta = getattr(response, "response_metadata", None) or {}
    usage = meta.get("token_usage") or meta.get("usage") or {}
    if isinstance(usage, dict):
        total += int(usage.get("total_tokens") or 0)
        if not total:
            total += int(usage.get("prompt_tokens") or 0) + int(usage.get("completion_tokens") or 0)
    usage_meta = getattr(response, "usage_metadata", None)
    if usage_meta:
        total += int(getattr(usage_meta, "total_tokens", 0) or usage_meta.get("total_tokens", 0) if isinstance(usage_meta, dict) else 0)
    return total

DEFAULT_SYSTEM_PROMPT = """You are an intelligent AI assistant with access to various tools.

## Your Capabilities
- Reason step-by-step to solve complex problems
- Use tools to gather information, perform calculations, and analyze data
- Provide clear, well-structured responses
- Cite sources and explain your reasoning

## Tool Usage Guidelines
1. When you need information you don't have, use the appropriate tool
2. Explain what you're doing when calling a tool
3. Base your answers on tool results, not speculation
4. If a tool fails, try an alternative approach or explain the limitation

## Response Format
- Use markdown for clear structure
- Include tables when comparing data
- Separate different topics with clear headings
"""


def normalize_agent_config(config: Optional[AgentConfig]) -> AgentConfig:
    """统一 Agent 运行配置，尊重客户端 provider/model。"""
    config = config or AgentConfig()
    if not config.provider:
        config.provider = app_config.agent.default_provider
    if not config.max_iterations:
        config.max_iterations = app_config.agent.max_iterations
    return config


def resolve_system_prompt(config: AgentConfig) -> str:
    """合并技能 Prompt 与 Agent 默认/自定义 Prompt。"""
    base_prompt = (config.system_prompt or DEFAULT_SYSTEM_PROMPT).strip()
    active_skill = skill_registry.get_active()
    if active_skill:
        skill_prompt = active_skill.get_system_prompt().strip()
        if skill_prompt:
            return f"{skill_prompt}\n\n{base_prompt}"
    return base_prompt


def get_langchain_tools(config: AgentConfig | None = None):
    """根据激活技能筛选可用工具。"""
    active_skill = skill_registry.get_active()
    if active_skill:
        required = active_skill.get_required_tools()
        if required:
            return tool_registry.to_langchain_tools(names=required)
    return tool_registry.to_langchain_tools()


def message_content(message: BaseMessage) -> str:
    """提取消息文本内容。"""
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif hasattr(block, "text"):
                parts.append(getattr(block, "text", ""))
        return "".join(parts)
    return str(content) if content else ""


async def load_agent_context(
    config: AgentConfig,
    user_input: str,
    system_prompt: str,
) -> tuple[str, list[dict]]:
    """加载记忆 + 知识库上下文并注入 System Prompt，返回 (context, citations)。"""
    active_skill = skill_registry.get_active()
    context_strategy = (
        active_skill.get_context_strategy() if active_skill else None
    )
    try:
        bundle = await asyncio.wait_for(
            memory_manager.load_context_bundle(
                config.session_id,
                user_input,
                system_prompt,
                context_strategy=context_strategy,
            ),
            timeout=CONTEXT_LOAD_TIMEOUT,
        )
        return bundle["context"], bundle.get("citations", [])
    except Exception as exc:
        print(f"[AgentRuntime] load_context skipped: {exc}")
        return system_prompt, []


async def build_initial_messages(
    config: AgentConfig,
    user_input: str,
) -> tuple[list[BaseMessage], list[dict]]:
    """构建带记忆上下文的初始消息列表，返回 (messages, citations)。"""
    system_prompt = resolve_system_prompt(config)
    context, citations = await load_agent_context(config, user_input, system_prompt)
    return [
        SystemMessage(content=context),
        HumanMessage(content=user_input),
    ], citations


def create_llm(config: AgentConfig, temperature: float | None = None) -> BaseChatModel:
    """创建 LLM 实例，使用配置中的 provider/model。"""
    kwargs = {"temperature": config.temperature if temperature is None else temperature}
    if config.model:
        kwargs["model"] = config.model
    return LLMFactory.create(provider=config.provider, **kwargs)


async def execute_tool_call(tool_call: dict) -> tuple[ToolMessage, dict]:
    """执行单个工具调用并返回 ToolMessage 与审计记录。"""
    tool_name = tool_call["name"]
    tool_args = tool_call.get("args") or {}
    tool_id = tool_call.get("id") or tool_name

    tool = tool_registry.get(tool_name)
    if not tool:
        error_text = f"Tool '{tool_name}' not found."
        record = {"tool": tool_name, "args": tool_args, "result": error_text}
        return (
            ToolMessage(content=error_text, tool_call_id=tool_id, name=tool_name),
            record,
        )

    result = await tool.execute(**tool_args)
    result_text = result.to_string()
    record = {"tool": tool_name, "args": tool_args, "result": result_text}
    return (
        ToolMessage(content=result_text, tool_call_id=tool_id, name=tool_name),
        record,
    )


async def invoke_llm_with_tools(
    llm: BaseChatModel,
    messages: list[BaseMessage],
    tools,
    max_iterations: int,
) -> tuple[str, list[dict]]:
    """
    运行 ReAct 工具循环（非流式），直到模型给出最终文本或达到迭代上限。
    """
    llm_with_tools = llm.bind_tools(tools)
    tool_calls_made: list[dict] = []
    final_output = ""

    for iteration in range(1, max_iterations + 1):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if getattr(response, "tool_calls", None):
            for tool_call in response.tool_calls:
                tool_message, record = await execute_tool_call(tool_call)
                tool_calls_made.append(record)
                messages.append(tool_message)
            continue

        final_output = message_content(response)
        break
    else:
        final_output = final_output or "已达到最大工具调用次数，请简化任务后重试。"

    return final_output, tool_calls_made


async def stream_text_as_reasoning(
    text: str,
    chunk_size: int = 24,
) -> AsyncIterator[AgentEvent]:
    """将完整文本切成 REASONING 事件，兼容前端 token/accumulated 字段。"""
    if not text:
        return

    accumulated = ""
    for index in range(0, len(text), chunk_size):
        token = text[index : index + chunk_size]
        accumulated += token
        yield AgentEvent(
            type=AgentEventType.REASONING,
            data={"token": token, "accumulated": accumulated},
        )


async def run_react_loop(
    user_input: str,
    config: AgentConfig,
    *,
    persist_memory: bool = True,
    thinking_message: str = "正在推理并决定是否调用工具...",
    emit_done: bool = True,
) -> AsyncIterator[AgentEvent]:
    """
    统一的 ReAct 执行循环（流式事件）。

    事件序列：THINKING → (TOOL_CALL/TOOL_RESULT)* → REASONING* → FINAL → DONE
    """
    config = normalize_agent_config(config)
    messages, citations = await build_initial_messages(config, user_input)
    if citations:
        yield AgentEvent(
            type=AgentEventType.CITATION,
            data={"citations": citations},
        )
    tools = get_langchain_tools(config)
    llm = create_llm(config)
    llm_with_tools = llm.bind_tools(tools)

    tool_calls_made: list[dict] = []
    final_output = ""
    tokens_used = 0
    start_time = time.time()

    try:
        for iteration in range(1, config.max_iterations + 1):
            yield AgentEvent(
                type=AgentEventType.THINKING,
                data={
                    "iteration": iteration,
                    "message": thinking_message,
                },
            )

            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)
            tokens_used += extract_token_usage(response)

            if getattr(response, "tool_calls", None):
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call.get("args") or {}
                    yield AgentEvent(
                        type=AgentEventType.TOOL_CALL,
                        data={"tool": tool_name, "args": tool_args},
                    )
                    tool_message, record = await execute_tool_call(tool_call)
                    tool_calls_made.append(record)
                    yield AgentEvent(
                        type=AgentEventType.TOOL_RESULT,
                        data={
                            "tool": tool_name,
                            "result": record["result"],
                        },
                    )
                    messages.append(tool_message)
                continue

            final_output = message_content(response)
            async for event in stream_text_as_reasoning(final_output):
                yield event
            break
        else:
            final_output = "已达到最大工具调用次数，请简化任务后重试。"
            async for event in stream_text_as_reasoning(final_output):
                yield event

        elapsed = (time.time() - start_time) * 1000
        yield AgentEvent(
            type=AgentEventType.FINAL,
            data={
                "output": final_output,
                "tool_calls": tool_calls_made,
                "execution_time_ms": elapsed,
                "tokens_used": tokens_used,
                "provider": config.provider,
                "model": config.model or (
                    app_config.providers[config.provider].model
                    if config.provider in app_config.providers else None
                ),
            },
        )

        if persist_memory and final_output:
            await memory_manager.save_context(
                config.session_id,
                user_input,
                final_output,
            )

        if emit_done:
            yield AgentEvent(type=AgentEventType.DONE)

    except Exception as exc:
        yield AgentEvent(
            type=AgentEventType.ERROR,
            data={"message": str(exc)},
        )
        if emit_done:
            yield AgentEvent(type=AgentEventType.DONE)


async def run_prompt_tool_loop(
    prompt: str,
    *,
    temperature: float = 0.4,
    tools,
    max_iterations: int = 5,
) -> AsyncIterator[AgentEvent]:
    """
    对单条 HumanMessage Prompt 运行工具循环（用于 Multi-Agent 角色调用）。
    """
    config = normalize_agent_config(AgentConfig(temperature=temperature))
    llm = create_llm(config, temperature=temperature)
    llm_with_tools = llm.bind_tools(tools)
    messages: list[BaseMessage] = [HumanMessage(content=prompt)]

    tool_calls_made: list[dict] = []
    final_output = ""

    for iteration in range(1, max_iterations + 1):
        yield AgentEvent(
            type=AgentEventType.THINKING,
            data={"iteration": iteration, "message": "角色正在推理..."},
        )

        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if getattr(response, "tool_calls", None):
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args") or {}
                yield AgentEvent(
                    type=AgentEventType.TOOL_CALL,
                    data={"tool": tool_name, "args": tool_args},
                )
                tool_message, record = await execute_tool_call(tool_call)
                tool_calls_made.append(record)
                yield AgentEvent(
                    type=AgentEventType.TOOL_RESULT,
                    data={"tool": tool_name, "result": record["result"]},
                )
                messages.append(tool_message)
            continue

        final_output = message_content(response)
        async for event in stream_text_as_reasoning(final_output):
            yield event
        break
    else:
        final_output = final_output or "已达到最大工具调用次数。"
        async for event in stream_text_as_reasoning(final_output):
            yield event

    yield AgentEvent(
        type=AgentEventType.FINAL,
        data={"output": final_output, "tool_calls": tool_calls_made},
    )


async def collect_prompt_tool_response(
    prompt: str,
    *,
    temperature: float = 0.4,
    tools,
    max_iterations: int = 5,
) -> tuple[str, list[dict]]:
    """收集 prompt 工具循环的最终输出。"""
    output = ""
    tool_calls: list[dict] = []
    async for event in run_prompt_tool_loop(
        prompt,
        temperature=temperature,
        tools=tools,
        max_iterations=max_iterations,
    ):
        if event.type == AgentEventType.FINAL:
            output = event.data.get("output", "")
            tool_calls = event.data.get("tool_calls", [])
    return output, tool_calls


async def collect_react_response(
    user_input: str,
    config: AgentConfig,
    *,
    persist_memory: bool = False,
) -> AgentResponse:
    """通过事件循环收集 ReAct 完整响应（供 invoke / 子 Agent 复用）。"""
    start_time = time.time()
    events: list[AgentEvent] = []
    output = ""
    tool_calls: list[dict] = []

    async for event in run_react_loop(
        user_input,
        config,
        persist_memory=persist_memory,
        thinking_message="正在执行 ReAct 推理循环...",
    ):
        events.append(event)
        if event.type == AgentEventType.FINAL:
            output = event.data.get("output", "")
            tool_calls = event.data.get("tool_calls", [])

    elapsed = (time.time() - start_time) * 1000
    return AgentResponse(
        output=output,
        events=events,
        tool_calls=tool_calls,
        execution_time_ms=elapsed,
        tokens_used=sum(
            int(e.data.get("tokens_used", 0))
            for e in events
            if e.type == AgentEventType.FINAL
        ),
    )

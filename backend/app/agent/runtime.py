"""
Agent 运行时共享模块
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.base import AgentConfig, AgentEvent, AgentEventType, AgentResponse
from app.core.config import config as app_config
from app.core.connection_context import set_connection_context, ConnectionContext
from app.llm.factory import LLMFactory
from app.memory.manager import memory_manager
from app.skills.registry import skill_registry
from app.tools.registry import tool_registry

FIXED_LLM_PROVIDER = "deepseek"
CONTEXT_LOAD_TIMEOUT = 10.0

DEFAULT_SYSTEM_PROMPT = """你是「财务智能助手」，隶属于本企业智能体平台，专注于财务、会计、审计、税务与报表分析场景。

## 身份与称呼（必须遵守）
- 当用户询问「你是谁」「你叫什么」「介绍一下自己」等身份问题时，只回答：你是**财务智能助手**（或**企业财务 AI 助手**），帮助用户处理财务分析、会计准则咨询、审计思路、报表解读、税务概要等问题。
- **禁止**自称 DeepSeek、ChatGPT、Claude、OpenAI、Anthropic 或任何底层大模型/厂商名称。
- **禁止**强调自己是「通用 AI」「语言模型」；以**财务助手**身份作答即可。
- 若被追问技术实现，可简要说明「基于企业智能体平台，结合知识库与工具辅助作答」，不必披露具体模型供应商。

## 能力范围
- 逐步推理，解决财务与会计相关的复杂问题
- 使用工具检索知识库、计算数据、分析报表
- 给出结构清晰、专业审慎的回答，并说明依据与假设
- 对不确定或需持证会计师/税务师判断的事项，明确提示咨询专业人士

## 工具使用
1. 缺少事实或准则依据时，优先调用知识检索/计算类工具
2. 说明正在使用的工具及目的
3. 基于工具结果作答，避免无依据臆测
4. 工具失败时尝试替代方案或说明限制

## 回答格式
- 使用 Markdown 结构化输出
- 比较数据时使用表格
- 不同主题用清晰小标题分隔
- 涉及准则时注明所依据的准则名称或来源（若已知）
"""


def extract_token_usage(response: AIMessage) -> int:
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


def normalize_agent_config(config: Optional[AgentConfig]) -> AgentConfig:
    config = config or AgentConfig()
    if not config.provider:
        config.provider = app_config.agent.default_provider
    if not config.max_iterations:
        config.max_iterations = app_config.agent.max_iterations
    return config


def _resolve_active_skill(config: AgentConfig):
    if config.active_skill:
        return skill_registry.get(config.active_skill)
    return None


def resolve_system_prompt(config: AgentConfig) -> str:
    base_prompt = (config.system_prompt or DEFAULT_SYSTEM_PROMPT).strip()
    active_skill = _resolve_active_skill(config)
    if active_skill:
        skill_prompt = active_skill.get_system_prompt().strip()
        if skill_prompt:
            return f"{skill_prompt}\n\n{base_prompt}"
    return base_prompt

def get_langchain_tools(config: AgentConfig | None = None):
    config = normalize_agent_config(config)
    active_skill = _resolve_active_skill(config)
    if active_skill:
        required = active_skill.get_required_tools()
        if required:
            return tool_registry.to_langchain_tools(names=required)
    return tool_registry.to_langchain_tools()


def message_content(message: BaseMessage) -> str:
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


def _ensure_tool_context(config: AgentConfig) -> None:
    ctx = ConnectionContext(
        user_id=config.user_id or 0,
        user_type=config.user_type,
        session_id=config.session_id,
        active_skill=config.active_skill,
    )
    set_connection_context(ctx)


async def load_agent_context(
    config: AgentConfig,
    user_input: str,
    system_prompt: str,
) -> tuple[str, list[dict]]:
    active_skill = _resolve_active_skill(config)
    context_strategy = config.context_strategy
    if context_strategy is None and active_skill:
        context_strategy = active_skill.get_context_strategy()
    try:
        bundle = await asyncio.wait_for(
            memory_manager.load_context_bundle(
                config.session_id,
                user_input,
                system_prompt,
                user_id=config.user_id,
                user_type=config.user_type,
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
    _ensure_tool_context(config)
    system_prompt = resolve_system_prompt(config)
    context, citations = await load_agent_context(config, user_input, system_prompt)
    attachments = config.attachments or []
    if attachments:
        from app.llm.providers import provider_supports_vision, pick_vision_provider
        from app.llm.vision import attachments_fallback_context, build_multimodal_human_message

        vision_provider = pick_vision_provider(config.provider)
        use_vision = bool(
            vision_provider
            and provider_supports_vision(vision_provider, config.model)
        )
        if use_vision:
            file_attachments = [
                a for a in attachments
                if a.get("kind") == "file" or a.get("file_path")
            ]
            file_context = attachments_fallback_context(file_attachments) if file_attachments else ""
            human = build_multimodal_human_message(
                user_input, attachments, fallback_text=file_context
            )
        else:
            fallback = attachments_fallback_context(attachments)
            combined = user_input.strip() or "请分析附件。"
            if fallback:
                combined = f"{combined}\n\n{fallback}"
            human = HumanMessage(content=combined)
        return [SystemMessage(content=context), human], citations
    return [
        SystemMessage(content=context),
        HumanMessage(content=user_input),
    ], citations


async def execute_tool_call(tool_call: dict) -> tuple[ToolMessage, dict]:
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
    chunk_size: int | None = None,
) -> AsyncIterator[AgentEvent]:
    if not text:
        return

    size = chunk_size if chunk_size is not None else _fallback_chunk_size()
    accumulated = ""
    for index in range(0, len(text), size):
        token = text[index : index + size]
        accumulated += token
        yield AgentEvent(
            type=AgentEventType.REASONING,
            data={"token": token, "accumulated": accumulated},
        )


@dataclass
class StreamRoundComplete:
    """Marker emitted at end of one LLM round (with optional tools)."""
    response: AIMessage
    accumulated_text: str
    is_tool_round: bool
    tokens_used: int = 0


@dataclass
class TextStreamComplete:
    """Marker emitted at end of a text-only LLM stream."""
    text: str
    tokens_used: int = 0


def _fallback_chunk_size() -> int:
    return app_config.agent.stream_fallback_chunk_size


def _use_streaming(config: AgentConfig) -> bool:
    return bool(config.streaming and app_config.agent.streaming_enabled)


def _chunk_has_tool_signal(chunk: BaseMessage) -> bool:
    tool_chunks = getattr(chunk, "tool_call_chunks", None)
    if tool_chunks:
        return True
    tool_calls = getattr(chunk, "tool_calls", None)
    return bool(tool_calls)


def _to_ai_message(message: BaseMessage) -> AIMessage:
    if isinstance(message, AIMessage):
        return message
    return AIMessage(
        content=message_content(message),
        tool_calls=list(getattr(message, "tool_calls", None) or []),
        response_metadata=dict(getattr(message, "response_metadata", None) or {}),
    )


async def _simulate_reasoning_events(text: str) -> AsyncIterator[AgentEvent]:
    async for event in stream_text_as_reasoning(text):
        yield event


async def _llm_round_events(
    llm_with_tools,
    messages: list[BaseMessage],
    config: AgentConfig,
) -> AsyncIterator[AgentEvent | StreamRoundComplete]:
    """Stream one ReAct LLM round; yields REASONING deltas then StreamRoundComplete."""
    if not _use_streaming(config):
        response = _to_ai_message(await llm_with_tools.ainvoke(messages))
        tokens = extract_token_usage(response)
        if response.tool_calls:
            yield StreamRoundComplete(
                response=response,
                accumulated_text="",
                is_tool_round=True,
                tokens_used=tokens,
            )
            return
        text = message_content(response)
        async for event in _simulate_reasoning_events(text):
            yield event
        yield StreamRoundComplete(
            response=response,
            accumulated_text=text,
            is_tool_round=False,
            tokens_used=tokens,
        )
        return

    gathered: BaseMessage | None = None
    accumulated = ""
    saw_tool_signal = False
    try:
        async for chunk in llm_with_tools.astream(messages):
            gathered = chunk if gathered is None else gathered + chunk
            if _chunk_has_tool_signal(chunk):
                saw_tool_signal = True
                continue
            delta = message_content(chunk)
            if delta and not saw_tool_signal:
                accumulated += delta
                yield AgentEvent(
                    type=AgentEventType.REASONING,
                    data={"token": delta, "accumulated": accumulated},
                )

        response = _to_ai_message(gathered if gathered is not None else AIMessage(content=""))
        tokens = extract_token_usage(response)
        is_tool_round = saw_tool_signal or bool(response.tool_calls)

        if is_tool_round:
            yield StreamRoundComplete(
                response=response,
                accumulated_text="",
                is_tool_round=True,
                tokens_used=tokens,
            )
            return

        final_text = message_content(response) or accumulated
        if final_text and not accumulated:
            async for event in _simulate_reasoning_events(final_text):
                yield event
        yield StreamRoundComplete(
            response=response,
            accumulated_text=final_text,
            is_tool_round=False,
            tokens_used=tokens,
        )
    except Exception as exc:
        print(f"[Streaming] fallback to simulated: {exc}")
        response = _to_ai_message(await llm_with_tools.ainvoke(messages))
        tokens = extract_token_usage(response)
        if response.tool_calls:
            yield StreamRoundComplete(
                response=response,
                accumulated_text="",
                is_tool_round=True,
                tokens_used=tokens,
            )
            return
        text = message_content(response)
        async for event in _simulate_reasoning_events(text):
            yield event
        yield StreamRoundComplete(
            response=response,
            accumulated_text=text,
            is_tool_round=False,
            tokens_used=tokens,
        )


async def stream_llm_text_events(
    llm: BaseChatModel,
    messages: list[BaseMessage],
    config: AgentConfig | None = None,
) -> AsyncIterator[AgentEvent | TextStreamComplete]:
    """Stream a text-only LLM call (no tools), e.g. debate judge summaries."""
    config = normalize_agent_config(config or AgentConfig())

    if not _use_streaming(config):
        response = _to_ai_message(await llm.ainvoke(messages))
        text = message_content(response)
        async for event in _simulate_reasoning_events(text):
            yield event
        yield TextStreamComplete(text=text, tokens_used=extract_token_usage(response))
        return

    gathered: BaseMessage | None = None
    accumulated = ""
    try:
        async for chunk in llm.astream(messages):
            gathered = chunk if gathered is None else gathered + chunk
            delta = message_content(chunk)
            if delta:
                accumulated += delta
                yield AgentEvent(
                    type=AgentEventType.REASONING,
                    data={"token": delta, "accumulated": accumulated},
                )
        response = _to_ai_message(gathered if gathered is not None else AIMessage(content=""))
        final_text = message_content(response) or accumulated
        if final_text and not accumulated:
            async for event in _simulate_reasoning_events(final_text):
                yield event
        yield TextStreamComplete(
            text=final_text,
            tokens_used=extract_token_usage(response),
        )
    except Exception as exc:
        print(f"[Streaming] fallback to simulated: {exc}")
        response = _to_ai_message(await llm.ainvoke(messages))
        text = message_content(response)
        async for event in _simulate_reasoning_events(text):
            yield event
        yield TextStreamComplete(text=text, tokens_used=extract_token_usage(response))


async def _emit_tool_round_events(
    response: AIMessage,
    tool_calls_made: list[dict],
) -> AsyncIterator[AgentEvent | ToolMessage]:
    """Execute tool calls from an LLM response; yields WS events and ToolMessages."""
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
        yield tool_message


async def run_react_loop(
    user_input: str,
    config: AgentConfig,
    *,
    persist_memory: bool = True,
    thinking_message: str = "正在推理并决定是否调用工具...",
    emit_done: bool = True,
) -> AsyncIterator[AgentEvent]:
    config = normalize_agent_config(config)
    _ensure_tool_context(config)
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

            round_complete: StreamRoundComplete | None = None
            async for item in _llm_round_events(llm_with_tools, messages, config):
                if isinstance(item, StreamRoundComplete):
                    round_complete = item
                else:
                    yield item

            if round_complete is None:
                final_output = "模型未返回有效响应，请重试。"
                break

            tokens_used += round_complete.tokens_used
            messages.append(round_complete.response)

            if round_complete.is_tool_round:
                async for item in _emit_tool_round_events(round_complete.response, tool_calls_made):
                    if isinstance(item, AgentEvent):
                        yield item
                    else:
                        messages.append(item)
                continue

            final_output = round_complete.accumulated_text
            break
        else:
            final_output = "已达到最大工具调用次数，请简化任务后重试。"
            async for event in _simulate_reasoning_events(final_output):
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
                user_id=config.user_id,
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


def create_llm(config: AgentConfig, temperature: float | None = None) -> BaseChatModel:
    kwargs = {"temperature": config.temperature if temperature is None else temperature}
    if config.model:
        kwargs["model"] = config.model
    if config.attachments:
        from app.llm.providers import get_provider_vision_meta, pick_vision_provider

        vision_provider = pick_vision_provider(config.provider)
        if vision_provider:
            meta = get_provider_vision_meta(vision_provider)
            if meta.vision_models and not kwargs.get("model"):
                kwargs["model"] = meta.vision_models[0]
            return LLMFactory.create(provider=vision_provider, **kwargs)
    return LLMFactory.create(provider=config.provider, **kwargs)


async def run_prompt_tool_loop(
    prompt: str,
    *,
    temperature: float = 0.4,
    tools,
    max_iterations: int = 5,
    config: AgentConfig | None = None,
) -> AsyncIterator[AgentEvent]:
    config = normalize_agent_config(config or AgentConfig(temperature=temperature))
    config.temperature = temperature
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

        round_complete: StreamRoundComplete | None = None
        async for item in _llm_round_events(llm_with_tools, messages, config):
            if isinstance(item, StreamRoundComplete):
                round_complete = item
            else:
                yield item

        if round_complete is None:
            final_output = "模型未返回有效响应。"
            break

        messages.append(round_complete.response)

        if round_complete.is_tool_round:
            async for item in _emit_tool_round_events(round_complete.response, tool_calls_made):
                if isinstance(item, AgentEvent):
                    yield item
                else:
                    messages.append(item)
            continue

        final_output = round_complete.accumulated_text
        break
    else:
        final_output = final_output or "已达到最大工具调用次数。"
        async for event in _simulate_reasoning_events(final_output):
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

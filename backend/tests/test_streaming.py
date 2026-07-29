"""Unit tests for LLM token streaming (PRD: LLM真流式输出)."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from app.agent.base import AgentConfig, AgentEvent, AgentEventType
from app.agent.runtime import (
    StreamRoundComplete,
    TextStreamComplete,
    _llm_round_events,
    stream_llm_text_events,
    stream_text_as_reasoning,
)


def _run(coro):
    return asyncio.run(coro)


async def _collect(async_gen):
    items = []
    async for item in async_gen:
        items.append(item)
    return items


class TestSimulatedStreaming(unittest.TestCase):
    def test_stream_text_as_reasoning_chunks(self):
        events = _run(_collect(stream_text_as_reasoning("Hello World!", chunk_size=5)))
        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[-1].data["accumulated"], "Hello World!")


class TestLlmRoundEvents(unittest.TestCase):
    @patch("app.agent.runtime._use_streaming", return_value=False)
    def test_text_only_round_when_streaming_disabled(self, _mock):
        llm = MagicMock()
        llm.ainvoke = AsyncMock(return_value=AIMessage(content="你好，世界"))

        async def _run_test():
            llm_with_tools = MagicMock()
            llm_with_tools.ainvoke = llm.ainvoke
            items = await _collect(
                _llm_round_events(
                    llm_with_tools,
                    [HumanMessage(content="hi")],
                    AgentConfig(streaming=False),
                )
            )
            reasoning = [i for i in items if isinstance(i, AgentEvent) and i.type == AgentEventType.REASONING]
            complete = [i for i in items if isinstance(i, StreamRoundComplete)]
            self.assertGreater(len(reasoning), 0)
            self.assertEqual(len(complete), 1)
            self.assertFalse(complete[0].is_tool_round)
            self.assertEqual(complete[0].accumulated_text, "你好，世界")

        _run(_run_test())

    @patch("app.agent.runtime._use_streaming", return_value=False)
    def test_tool_round_when_streaming_disabled(self, _mock):
        async def _run_test():
            llm_with_tools = MagicMock()
            llm_with_tools.ainvoke = AsyncMock(
                return_value=AIMessage(
                    content="",
                    tool_calls=[{"name": "calculator", "args": {"a": 1}, "id": "t1"}],
                )
            )
            items = await _collect(
                _llm_round_events(
                    llm_with_tools,
                    [HumanMessage(content="calc")],
                    AgentConfig(streaming=False),
                )
            )
            reasoning = [i for i in items if isinstance(i, AgentEvent) and i.type == AgentEventType.REASONING]
            complete = [i for i in items if isinstance(i, StreamRoundComplete)]
            self.assertEqual(len(reasoning), 0)
            self.assertTrue(complete[0].is_tool_round)

        _run(_run_test())

    @patch("app.agent.runtime._use_streaming", return_value=True)
    def test_astream_text_emits_reasoning_deltas(self, _mock):
        chunks = [AIMessageChunk(content="你"), AIMessageChunk(content="好")]

        async def _run_test():
            class FakeLLM:
                async def astream(self, messages):
                    for chunk in chunks:
                        yield chunk

            llm_with_tools = FakeLLM()
            items = await _collect(
                _llm_round_events(
                    llm_with_tools,
                    [HumanMessage(content="hi")],
                    AgentConfig(streaming=True),
                )
            )
            reasoning = [i for i in items if isinstance(i, AgentEvent) and i.type == AgentEventType.REASONING]
            complete = [i for i in items if isinstance(i, StreamRoundComplete)]
            self.assertEqual(len(reasoning), 2)
            self.assertEqual(reasoning[0].data["token"], "你")
            self.assertEqual(reasoning[1].data["accumulated"], "你好")
            self.assertFalse(complete[0].is_tool_round)

        _run(_run_test())

    @patch("app.agent.runtime._use_streaming", return_value=True)
    def test_astream_failure_falls_back_to_ainvoke(self, _mock):
        async def _run_test():
            llm_with_tools = MagicMock()

            async def failing_astream(_messages):
                raise RuntimeError("stream unsupported")
                yield  # pragma: no cover

            llm_with_tools.astream = failing_astream
            llm_with_tools.ainvoke = AsyncMock(return_value=AIMessage(content="fallback text"))
            items = await _collect(
                _llm_round_events(
                    llm_with_tools,
                    [HumanMessage(content="hi")],
                    AgentConfig(streaming=True),
                )
            )
            complete = [i for i in items if isinstance(i, StreamRoundComplete)]
            self.assertEqual(complete[0].accumulated_text, "fallback text")

        _run(_run_test())


class TestTextStreamEvents(unittest.TestCase):
    @patch("app.agent.runtime._use_streaming", return_value=False)
    def test_text_stream_complete(self, _mock):
        async def _run_test():
            llm = MagicMock()
            llm.ainvoke = AsyncMock(return_value=AIMessage(content="裁决意见"))
            items = await _collect(
                stream_llm_text_events(llm, [HumanMessage(content="judge")], AgentConfig())
            )
            complete = [i for i in items if isinstance(i, TextStreamComplete)]
            self.assertEqual(complete[0].text, "裁决意见")

        _run(_run_test())


if __name__ == "__main__":
    unittest.main()

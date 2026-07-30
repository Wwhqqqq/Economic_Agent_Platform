"""Batch 5 acceptance tests — VLM charts + chat vision."""
from __future__ import annotations

import io

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw

from app.agent.base import AgentConfig
from app.agent.runtime import build_initial_messages
from app.ingestion.media.image_classifier_v2 import classify_image_v2
from app.ingestion.media.service import parse_image_bytes, parse_chat_attachment
from app.ingestion.media.vlm import describe_image, structured_to_facts
from app.llm.providers import pick_vision_provider, provider_supports_vision
from app.llm.vision import attachments_fallback_context, build_multimodal_human_message
from app.rag.query_router import get_query_router
from langchain_core.messages import HumanMessage


def _make_chart_png() -> bytes:
    img = Image.new("RGB", (400, 260), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle((60, 60, 100, 180), fill=(79, 70, 229))
    draw.rectangle((140, 80, 180, 180), fill=(99, 102, 241))
    draw.text((50, 20), "2024营收柱状图 Q1 1.2亿元 Q2 1.5亿元", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_decorative_png() -> bytes:
    img = Image.new("RGB", (24, 24), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_classifier_v2_chart_and_decorative():
    chart = classify_image_v2(
        width=400, height=260,
        ocr_text="2024营收柱状图 Q1 1.2亿元",
        ocr_quality=0.6,
        caption_hint="图1 营收",
    )
    assert chart.image_class == "chart"
    assert chart.skip_index is False

    deco = classify_image_v2(width=24, height=24, ocr_text="", ocr_quality=0.0)
    assert deco.image_class == "decorative"
    assert deco.skip_index is True


def test_vlm_heuristic_without_vision_api():
    result = describe_image(_make_chart_png(), image_class="chart", ocr_text="Q1 1.2亿元 Q2 1.5亿元 上升")
    assert result.engine in ("heuristic", "vision:openai", "vision:anthropic", "ocr_caption")
    assert result.caption or result.structured


def test_decorative_image_skips_indexing():
    parsed = parse_image_bytes(
        _make_decorative_png(),
        user_id=1,
        doc_id="doc-deco",
        filename="dot.png",
        index=True,
    )
    assert parsed.skip_index is True
    assert parsed.chunks == []
    assert parsed.parse_status == "skipped"


def test_chat_attachment_degrades_without_crash():
    meta = parse_chat_attachment(_make_chart_png(), user_id=1, filename="chart.png")
    assert meta["asset_id"]
    assert meta.get("data_url", "").startswith("data:image/")
    assert meta.get("ocr_text") is not None or meta.get("vlm_caption") is not None


def test_runtime_multimodal_fallback_without_vision():
    attachments = [{
        "ocr_text": "柱状图 Q1 1.2亿元",
        "vlm_caption": "营收呈上升趋势",
    }]
    config = AgentConfig(provider="deepseek", attachments=attachments)
    import asyncio

    async def _run():
        messages, _ = await build_initial_messages(config, "描述这张图表的趋势")
        assert len(messages) == 2
        human = messages[1]
        assert isinstance(human, HumanMessage)
        content = human.content if isinstance(human.content, str) else str(human.content)
        assert "柱状图" in content or "趋势" in content

    asyncio.run(_run())


def test_query_router_figure_intent():
    plan = get_query_router().analyze("这张图表的趋势是什么？")
    assert plan.needs_figure is True
    assert "figure_summary" in (plan.content_types or [])


def test_structured_to_facts_high_confidence_only():
    structured = {
        "key_figures": [{"label": "Q1营收", "value": "1.2", "unit": "亿元"}],
        "trends": ["上升"],
    }
    facts = structured_to_facts(
        structured,
        doc_id="d1",
        asset_id="a1",
        page_no=3,
        min_confidence=0.75,
    )
    assert len(facts) == 1
    assert facts[0].metric_name == "Q1营收"
    assert facts[0].source_page == 3


def test_vision_helpers():
    msg = build_multimodal_human_message("分析", [{"url": "data:image/png;base64,abc"}])
    assert isinstance(msg.content, list)
    fallback = attachments_fallback_context([{"ocr_text": "test ocr", "vlm_caption": "caption"}])
    assert "test ocr" in fallback
    # deepseek has no vision — should not crash pick_vision_provider
    assert provider_supports_vision("deepseek") is False

"""
实体抽取 — 从文本中提取知识图谱实体（规则 + 启发式）

用于：知识库入库、对话情景记忆、图谱检索增强。
"""
from __future__ import annotations

import json
import re
from typing import Any


FINANCIAL_KEYWORDS = {
    "资产负债表": "FinancialStatement",
    "利润表": "FinancialStatement",
    "现金流量表": "FinancialStatement",
    "审计": "AuditTopic",
    "财务比率": "FinancialMetric",
    "杜邦分析": "AnalysisMethod",
    "ROE": "FinancialMetric",
    "营收": "FinancialMetric",
    "净利润": "FinancialMetric",
}

ENTITY_TYPE_BY_KEYWORD = {
    "公司": "Company",
    "集团": "Company",
    "银行": "Company",
    "科技": "Company",
    "审计": "AuditTopic",
    "报告": "Document",
}


def extract_json_blob(text: str) -> dict | None:
    """尝试从文本中提取 JSON 对象。"""
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
    return None


def extract_entities(text: str, limit: int = 12) -> list[dict]:
    """
    从文本提取实体列表。

    Returns:
        [{"name": "...", "type": "...", "properties": {...}}, ...]
    """
    if not text or not text.strip():
        return []

    seen: set[str] = set()
    entities: list[dict] = []

    def _add(name: str, entity_type: str, **properties: Any) -> None:
        name = name.strip()
        if len(name) < 2 or name in seen:
            return
        seen.add(name)
        entities.append(
            {
                "name": name,
                "type": entity_type,
                "properties": properties,
            }
        )

    for keyword, entity_type in FINANCIAL_KEYWORDS.items():
        if keyword in text:
            _add(keyword, entity_type, source="keyword")

    for keyword, entity_type in ENTITY_TYPE_BY_KEYWORD.items():
        pattern = rf"([\u4e00-\u9fff]{{2,10}}{keyword})"
        for match in re.findall(pattern, text):
            _add(match, entity_type, source="pattern")

    for match in re.findall(r"[\u4e00-\u9fff]{2,8}", text):
        if match in FINANCIAL_KEYWORDS:
            continue
        if any(ch in match for ch in "的了是在有和与及"):
            continue
        _add(match, "Concept", source="cn_token")

    for match in re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", text):
        _add(match, "Organization", source="en_proper")

    for match in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text):
        _add(match, "Organization", source="en_phrase")

    return entities[:limit]


def build_document_title(content: str, doc_id: str) -> str:
    """生成文档标题（首行或截断内容）。"""
    first_line = content.strip().splitlines()[0] if content.strip() else doc_id
    title = first_line.strip()[:80]
    return title or doc_id

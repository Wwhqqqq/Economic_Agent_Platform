from __future__ import annotations

import re
from dataclasses import dataclass, field


FIGURE_KEYWORDS = ["图表", "图", "figure", "chart", "趋势", "柱状", "折线", "饼图", "示意图"]
FACT_KEYWORDS = [
    "多少", "数值", "金额", "是多少", "ROE", "资产负债率", "货币资金", "净利润",
    "营业收入", "资产总计", "负债", "ratio", "percent", "%",
]
RELATION_KEYWORDS = ["关联", "关系", "供应商", "董事", "股东", "审计师"]
TABLE_KEYWORDS = ["表格", "科目", "三表", "资产负债表", "利润表", "现金流量表"]


@dataclass
class QueryPlan:
    intent: str = "general_qa"
    entities: list[str] = field(default_factory=list)
    time_range: str | None = None
    needs_table: bool = False
    needs_graph_hop: bool = False
    needs_fact: bool = False
    needs_figure: bool = False
    vector_weight: float = 1.0
    graph_weight: float = 1.0
    fact_weight: float = 0.0
    content_types: list[str] | None = None


class QueryRouter:
    PERIOD_PATTERN = re.compile(r"(20\d{2}|19\d{2})(?:年|Q[1-4])?")

    def analyze(self, query: str) -> QueryPlan:
        q = query.strip()
        plan = QueryPlan()
        plan.entities = self._extract_entities(q)
        m = self.PERIOD_PATTERN.search(q)
        if m:
            plan.time_range = m.group(0)

        if self._is_fact_lookup(q):
            plan.intent = "fact_lookup"
            plan.needs_fact = True
            plan.needs_table = True
            plan.vector_weight = 0.6
            plan.graph_weight = 0.4
            plan.fact_weight = 1.5
            plan.content_types = ["table_row", "table_summary", "paragraph"]
        elif self._needs_figure(q):
            plan.intent = "figure_lookup"
            plan.needs_figure = True
            plan.vector_weight = 1.2
            plan.graph_weight = 0.5
            plan.fact_weight = 0.6
            plan.content_types = ["figure_summary", "paragraph"]
        elif self._is_relation(q):
            plan.intent = "relation_explore"
            plan.needs_graph_hop = True
            plan.vector_weight = 0.5
            plan.graph_weight = 1.5
            plan.fact_weight = 0.3
        elif self._needs_table(q):
            plan.intent = "table_lookup"
            plan.needs_table = True
            plan.vector_weight = 1.0
            plan.graph_weight = 0.8
            plan.fact_weight = 0.8
            plan.content_types = ["table_row", "table_summary"]
        else:
            plan.intent = "concept_explain"
            plan.vector_weight = 1.0
            plan.graph_weight = 0.8
            plan.fact_weight = 0.2

        return plan

    def _is_fact_lookup(self, q: str) -> bool:
        if any(kw in q for kw in FACT_KEYWORDS):
            return bool(re.search(r"[\d]|\?|？|多少|是什么", q))
        return bool(re.search(r"(20\d{2}).*(多少|是)", q))

    def _needs_figure(self, q: str) -> bool:
        return any(kw in q for kw in FIGURE_KEYWORDS)

    def _is_relation(self, q: str) -> bool:
        return any(kw in q for kw in RELATION_KEYWORDS)

    def _needs_table(self, q: str) -> bool:
        return any(kw in q for kw in TABLE_KEYWORDS)

    def _extract_entities(self, q: str) -> list[str]:
        entities: list[str] = []
        cn = re.findall(r"[\u4e00-\u9fff]{2,8}", q)
        for word in cn:
            if word in ("公司", "报告", "年度", "财务", "数据"):
                continue
            if len(word) >= 2:
                entities.append(word)
        return list(dict.fromkeys(entities))[:5]


_router: QueryRouter | None = None


def get_query_router() -> QueryRouter:
    global _router
    if _router is None:
        _router = QueryRouter()
    return _router

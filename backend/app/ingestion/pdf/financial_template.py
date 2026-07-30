from __future__ import annotations

import re

FINANCIAL_SECTIONS = {
    "balance_sheet": ["资产负债表", "合并资产负债表"],
    "income_statement": ["利润表", "合并利润表", "综合收益"],
    "cash_flow": ["现金流量表", "合并现金流量表"],
    "audit_opinion": ["审计意见", "审计报告", "注册会计师"],
    "notes": ["财务报表附注", "附注"],
}

FINANCIAL_REPORT_KEYWORDS = [
    "年度报告", "审计报告", "财务报表", "资产负债表", "利润表", "现金流量表",
]


def detect_financial_report(text: str) -> bool:
    hits = sum(1 for kw in FINANCIAL_REPORT_KEYWORDS if kw in text)
    return hits >= 2


def detect_section(text: str) -> str | None:
    for section_id, keywords in FINANCIAL_SECTIONS.items():
        if any(kw in text for kw in keywords):
            return section_id
    return None


def enrich_tables_with_sections(tables, plain_text: str):
    """Assign section_path to tables based on nearby financial section headers."""
    current_section = ""
    lines = plain_text.splitlines()
    section_by_page: dict[int, str] = {}
    page_no = 1
    for line in lines:
        if line.startswith("[Page "):
            m = re.search(r"\[Page (\d+)\]", line)
            if m:
                page_no = int(m.group(1))
            continue
        section = detect_section(line)
        if section:
            label_map = {
                "balance_sheet": "资产负债表",
                "income_statement": "利润表",
                "cash_flow": "现金流量表",
                "audit_opinion": "审计意见",
                "notes": "附注",
            }
            current_section = label_map.get(section, line.strip())
        if current_section:
            section_by_page[page_no] = current_section

    for table in tables:
        table.section_path = section_by_page.get(table.page_no, table.section_path or "")
        if not table.caption and table.section_path:
            table.caption = f"{table.section_path} (p{table.page_no})"
    return tables

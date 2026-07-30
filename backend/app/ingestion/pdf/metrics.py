from __future__ import annotations

import re

METRIC_ALIASES = {
    "货币资金": "cash_and_equivalents",
    "应收账款": "accounts_receivable",
    "存货": "inventory",
    "固定资产": "fixed_assets",
    "资产总计": "total_assets",
    "负债合计": "total_liabilities",
    "所有者权益": "total_equity",
    "营业收入": "revenue",
    "净利润": "net_profit",
    "经营活动现金流量净额": "operating_cash_flow",
}


def standardize_metric(name: str) -> tuple[str, str]:
    cleaned = name.strip()
    code = METRIC_ALIASES.get(cleaned, "")
    if not code:
        code = re.sub(r"\s+", "_", cleaned.lower())[:64]
    return cleaned, code

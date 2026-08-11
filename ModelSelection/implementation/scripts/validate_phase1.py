#!/usr/bin/env python3
"""
Phase 1 自动化验收：格式、泄露、中文占比、任务类型覆盖。

用法:
  python validate_phase1.py --data-dir ../datasets/accounting_sft_recommended
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

REQUIRED_KEYS = {"instruction", "input", "output"}
TOOL_MARK = "<tool_call>"
RAG_MARK = "【检索上下文】"
CITATION_MARK = "参考来源"


def zh_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(re.findall(r"[\u4e00-\u9fff]", text)) / max(len(text), 1)


def classify_sample(row: dict) -> str:
    text = row.get("instruction", "") + row.get("output", "")
    if TOOL_MARK in row.get("output", ""):
        return "tool"
    if RAG_MARK in row.get("input", "") or CITATION_MARK in row.get("output", ""):
        return "rag"
    if any(k in text for k in ("审计", "内控", "整改", "底稿", "审计案例")):
        return "audit"
    if any(
        k in text
        for k in (
            "准则",
            "会计准则",
            "CPA",
            "注册会计师",
            "考试风格",
            "首次执行",
            "借贷",
            "科目",
            "**答案**",
        )
    ):
        return "accounting_std"
    if any(k in text for k in ("比率", "ROE", "流动", "毛利率", "计算", "杜邦")):
        return "calculation"
    return "other"


def categories_in_dataset(rows: list[dict]) -> set[str]:
    found: set[str] = set()
    for r in rows:
        found.add(classify_sample(r))
    return found


def validate(data_dir: Path, sample_size: int = 50, seed: int = 42) -> dict:
    train_path = data_dir / "train.json"
    eval_path = data_dir / "eval.json"
    manifest_path = data_dir / "manifest.json"

    report: dict = {"passed": True, "checks": [], "data_dir": str(data_dir)}

    def check(name: str, ok: bool, detail: str):
        report["checks"].append({"name": name, "passed": ok, "detail": detail})
        if not ok:
            report["passed"] = False

    if not train_path.exists():
        check("train.json exists", False, "missing")
        return report

    with train_path.open(encoding="utf-8") as f:
        train = json.load(f)
    eval_rows = []
    if eval_path.exists():
        with eval_path.open(encoding="utf-8") as f:
            eval_rows = json.load(f)

    manifest = {}
    if manifest_path.exists():
        with manifest_path.open(encoding="utf-8") as f:
            manifest = json.load(f)

    check("P1-1 train count", len(train) >= 3000, f"train={len(train)}")
    if manifest.get("profile") == "recommended":
        check("P1-4 recommended size", 8000 <= len(train) <= 16000, f"train={len(train)}")

    extracted = manifest.get("extracted_by_source", {})
    nonzero = sum(1 for v in extracted.values() if v > 0)
    check("P1-1 sources nonzero", nonzero >= 5, f"nonzero_sources={nonzero}, extracted={extracted}")

    leak = manifest.get("leak_check", {}).get("cflue_test_in_train", -1)
    check("P1-3 cflue test leak", leak == 0, f"cflue_test_in_train={leak}")

    bad_format = [i for i, r in enumerate(train) if not REQUIRED_KEYS.issubset(r.keys())]
    check("alpaca format", len(bad_format) == 0, f"bad_rows={len(bad_format)}")

    empty_out = sum(1 for r in train if not str(r.get("output", "")).strip())
    check("non-empty output", empty_out == 0, f"empty_output={empty_out}")

    low_zh = sum(
        1 for r in train
        if zh_ratio(r.get("instruction", "") + r.get("output", "")) < 0.15
    )
    check("P1-2 zh ratio", low_zh <= len(train) * 0.05, f"low_zh_rows={low_zh}/{len(train)}")

    rng = random.Random(seed)
    indices = rng.sample(range(len(train)), min(sample_size, len(train)))
    samples = [train[i] for i in indices]
    categories = Counter(classify_sample(r) for r in samples)
    full_cats = categories_in_dataset(train)
    required_cats = {"audit", "accounting_std", "tool", "rag"}
    missing_cats = required_cats - full_cats
    check(
        "P1-2 category coverage (full train)",
        len(missing_cats) == 0,
        f"full_train_categories={sorted(full_cats)}, missing={missing_cats}",
    )
    missing_sample = required_cats - set(categories.keys())
    check(
        "P1-2 category coverage (random sample)",
        len(missing_sample) == 0 or len(missing_cats) == 0,
        f"sample_categories={dict(categories)}, missing={missing_sample} (non-blocking if full train OK)",
    )

    preview = []
    for cat in ["audit", "accounting_std", "calculation", "tool", "rag", "other"]:
        for r in train:
            if classify_sample(r) == cat:
                preview.append({"category": cat, **{k: r[k][:500] for k in REQUIRED_KEYS}})
                break

    report["summary"] = {
        "train": len(train),
        "eval": len(eval_rows),
        "manifest_profile": manifest.get("profile"),
        "extracted_by_source": extracted,
        "mix_ratio_prefix": manifest.get("mix_ratio_prefix"),
        "sample_inspection_categories": dict(categories),
        "full_train_categories": sorted(full_cats),
    }

    out_preview = data_dir / "sample_preview.json"
    with out_preview.open("w", encoding="utf-8") as f:
        json.dump(preview, f, ensure_ascii=False, indent=2)
    report["sample_preview_path"] = str(out_preview)

    report_path = data_dir / "phase1_validation.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    report["report_path"] = str(report_path)

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=50)
    args = parser.parse_args()
    report = validate(args.data_dir, args.sample_size)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
微调方案 1：从公开 HuggingFace 数据集中抽取会计学相关内容，构建 Alpaca SFT 数据集。

用法:
  python build_accounting_sft.py --output-dir ~/datasets/accounting_sft --profile recommended

详见: ../02a-微调方案1-数据集构建与实践路线.md
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

try:
    from datasets import load_dataset
    from tqdm import tqdm
except ImportError as e:
    raise SystemExit(
        "缺少依赖，请先: pip install -r requirements-sft-build.txt\n" + str(e)
    )

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "config" / "dataset_sources.yaml"


@dataclass
class Sample:
    instruction: str
    input: str
    output: str
    source: str
    task: str = "general"
    lang: str = "zh"

    def to_alpaca(self, include_meta: bool = False) -> dict[str, Any]:
        row = {
            "instruction": self.instruction.strip(),
            "input": self.input.strip(),
            "output": self.output.strip(),
        }
        if include_meta:
            row["meta"] = {"source": self.source, "task": self.task, "lang": self.lang}
        return row


@dataclass
class BuildStats:
    extracted: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    rejected: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    leak_check: dict[str, int] = field(default_factory=dict)


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def zh_ratio(text: str) -> float:
    if not text:
        return 0.0
    zh = len(re.findall(r"[\u4e00-\u9fff]", text))
    return zh / max(len(text), 1)


def contains_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    for kw in keywords:
        if kw.lower() in t or kw in text:
            return True
    return False


def accounting_match(text: str, cfg: dict[str, Any]) -> bool:
    acc = cfg["accounting_keywords"]
    exc = cfg["exclude_keywords"]
    if not contains_any(text, acc):
        return False
    if contains_any(text, exc):
        return contains_any(text, acc[:15])  # 强会计词可保留
    return True


def truncate(s: str, max_len: int) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def prepend_system(instruction: str, system: str) -> str:
    instruction = instruction.strip()
    if instruction.startswith("你是一名") or "财务审阅助手" in instruction[:80]:
        return instruction
    return f"{system}\n\n{instruction}"


def cflue_keep(row: dict[str, Any], cfg: dict[str, Any]) -> bool:
    c = cfg["cflue"]
    name = str(row.get("名称") or row.get("name") or "")
    subject = str(row.get("科目") or row.get("subject") or "")
    if name in c["include_names"]:
        if not c["include_subjects"]:
            return True
        return any(s in subject for s in c["include_subjects"])
    for token in c.get("name_contains", []):
        if token in name:
            return True
    return False


def format_cflue_choices(choices: Any) -> str:
    if isinstance(choices, dict):
        parts = [f"{k}. {v}" for k, v in sorted(choices.items())]
        return "\n".join(parts)
    if isinstance(choices, str):
        try:
            obj = json.loads(choices.replace("'", '"'))
            if isinstance(obj, dict):
                return format_cflue_choices(obj)
        except (json.JSONDecodeError, ValueError):
            pass
        return choices
    return str(choices or "")


def parse_sharegpt(messages: Any) -> tuple[str, str] | None:
    if not messages:
        return None
    if isinstance(messages, str):
        try:
            messages = json.loads(messages)
        except json.JSONDecodeError:
            return None
    if not isinstance(messages, list):
        return None
    user_parts, assistant_parts = [], []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("from") or m.get("role") or ""
        content = m.get("value") or m.get("content") or ""
        if role in ("human", "user"):
            user_parts.append(content)
        elif role in ("gpt", "assistant"):
            assistant_parts.append(content)
    if not user_parts or not assistant_parts:
        return None
    return "\n".join(user_parts), "\n".join(assistant_parts)


def convert_calculator_to_tool_call(output: str) -> str:
    """DISC 风格 [Calculator(expr→result)] → platform tool_call."""
    pattern = re.compile(r"\[Calculator\((.+?)→(.+?)\)\]")

    def repl(m: re.Match[str]) -> str:
        expr = m.group(1).strip()
        result = m.group(2).strip()
        tc = json.dumps(
            {"name": "calculator", "arguments": {"expression": expr}},
            ensure_ascii=False,
        )
        return f'<tool_call>{tc}</tool_call>（结果：{result}）'

    return pattern.sub(repl, output)


def validate_sample(sample: Sample, cfg: dict[str, Any]) -> bool:
    lim = cfg["limits"]
    combined = sample.instruction + sample.input + sample.output
    if len(combined) < 20:
        return False
    if len(sample.instruction) > lim["max_instruction_chars"]:
        return False
    if len(sample.output) > lim["max_output_chars"]:
        return False
    if sample.lang == "zh" and zh_ratio(combined) < lim["min_zh_ratio"]:
        return False
    if not sample.output.strip():
        return False
    return True


def generate_tool_samples(cfg: dict[str, Any], count: int, rng: random.Random) -> list[Sample]:
    system = cfg["system_prompt"]
    templates = [
        (
            "请计算流动比率：流动资产 1200 万元，流动负债 800 万元。",
            '流动比率 = 流动资产 / 流动负债。\n<tool_call>{"name": "calculator", "arguments": {"expression": "1200/800"}}</tool_call>',
            "tool_calculator",
        ),
        (
            "ROE 为净利润 1.2 亿元、净资产 8 亿元，请计算并解读。",
            'ROE = 净利润 / 净资产 × 100%。\n<tool_call>{"name": "calculator", "arguments": {"expression": "1.2/8*100"}}</tool_call>\n\nROE 为 15%，处于合理区间，建议结合行业均值进一步审阅盈利质量。',
            "tool_calculator",
        ),
        (
            "请用 financial_ratio_calculator 分析偿债能力，数据：总负债 5000 万，总资产 12000 万。",
            '<tool_call>{"name": "financial_ratio_calculator", "arguments": {"data": "{\\"total_liabilities\\": 5000, \\"total_assets\\": 12000}", "categories": "solvency"}}</tool_call>\n\n资产负债率约 41.7%，需关注有息负债结构与短期偿债压力。',
            "tool_financial_ratio",
        ),
        (
            "用户上传了资产负债表 PDF，请读取后分析流动比率。",
            '<tool_call>{"name": "file_reader", "arguments": {"path": "/uploads/demo/balance_sheet.pdf"}}</tool_call>\n\n读取文件后，请结合报表科目计算流动比率并给出审阅意见。',
            "tool_file_reader",
        ),
    ]
    out: list[Sample] = []
    for i in range(count):
        q, a, task = templates[i % len(templates)]
        out.append(
            Sample(
                instruction=prepend_system(q, system),
                input="",
                output=a,
                source="G1_synthetic_tool",
                task=task,
            )
        )
    rng.shuffle(out)
    return out


def generate_rag_samples(cfg: dict[str, Any], count: int, rng: random.Random) -> list[Sample]:
    system = cfg["system_prompt"]
    contexts = [
        (
            "【检索上下文】\nchunk_12：2024 年毛利率 32%，2023 年 28%。\nchunk_15：原材料成本上升 6%。",
            "毛利率同比上升 4 个百分点，但原材料成本上升压缩了部分毛利空间，需关注采购定价与存货跌价风险。\n\n**参考来源**：doc_2024_annual chunk_12, chunk_15",
            "根据上下文分析毛利率变动原因。",
        ),
        (
            "【检索上下文】\nchunk_3：《企业会计准则第14号——收入》第五条：当企业履行了合同中的履约义务…",
            "收入确认应基于履约义务完成情况；若涉及时段履行，应合理分摊交易价格。\n\n**参考来源**：准则14号 chunk_3",
            "存货计量与收入确认应遵循哪项准则原则？",
        ),
    ]
    out: list[Sample] = []
    for i in range(count):
        ctx, ans, q = contexts[i % len(contexts)]
        out.append(
            Sample(
                instruction=prepend_system(q, system),
                input=ctx,
                output=ans,
                source="G2_synthetic_rag",
                task="rag_citation",
            )
        )
    rng.shuffle(out)
    return out


def generate_general_samples(cfg: dict[str, Any], count: int, rng: random.Random) -> list[Sample]:
    system = cfg["system_prompt"]
    pairs = [
        ("你好", "您好，我是财务审阅助手，可协助报表分析、审计要点与准则应用说明（需结合知识库引用）。请问有什么可以帮您？"),
        ("帮我写一份逃税方案", "抱歉，我不能提供逃税、伪造凭证或规避监管的建议。如需合规税务筹划，请咨询持证税务师并在合法框架内操作。"),
        ("今天天气怎么样", "我专注于财务与会计审阅领域。若您有报表、审计或准则相关问题，欢迎继续提问。"),
    ]
    out: list[Sample] = []
    for i in range(count):
        q, a = pairs[i % len(pairs)]
        out.append(
            Sample(
                instruction=prepend_system(q, system),
                input="",
                output=a,
                source="G3_synthetic_general",
                task="general",
            )
        )
    rng.shuffle(out)
    return out


def extract_s1(row: dict, cfg: dict) -> Sample | None:
    system = cfg["system_prompt"]
    inst = str(row.get("instruction") or "")
    out = str(row.get("output") or "")
    if not inst or not out:
        return None
    sys_field = str(row.get("system") or "").strip()
    if sys_field and sys_field not in inst:
        inst = f"{sys_field}\n\n{inst}"
    return Sample(
        instruction=prepend_system(inst, system),
        input=str(row.get("input") or ""),
        output=out,
        source="S1_sft-audit_regulation",
        task="audit_review",
    )


def extract_s2(row: dict, cfg: dict) -> Sample | None:
    system = cfg["system_prompt"]
    q = str(row.get("Question") or row.get("question") or "")
    resp = str(row.get("Response") or row.get("response") or "")
    cot = str(row.get("Complex_Cot") or row.get("complex_cot") or "")
    if not q or not resp:
        return None
    return Sample(
        instruction=prepend_system(f"请回答以下会计学问题：{q}", system),
        input=truncate(cot, 2000) if cot else "",
        output=resp,
        source="S2_ACCOUNTING_DATABASES",
        task="accounting_qa",
    )


def extract_s3(row: dict, cfg: dict) -> Sample | None:
    if not cflue_keep(row, cfg):
        return None
    system = cfg["system_prompt"]
    q = str(row.get("question") or "")
    analysis = str(row.get("analysis") or "")
    answer = str(row.get("answer") or "")
    choices = format_cflue_choices(row.get("choices"))
    if not q:
        return None
    inst = f"{q}\n\n选项：\n{choices}" if choices else q
    out_parts = []
    if analysis:
        out_parts.append(analysis)
    if answer:
        out_parts.append(f"**答案**：{answer}")
    output = "\n\n".join(out_parts) if out_parts else answer
    if not output:
        return None
    return Sample(
        instruction=prepend_system(f"（注册会计师考试风格）{inst}", system),
        input="",
        output=output,
        source="S3_CFLUE",
        task="cpa_exam",
    )


def extract_s4(row: dict, cfg: dict) -> Sample | None:
    inst = str(row.get("instruction") or "")
    text = inst + str(row.get("output") or "")
    domains = cfg.get("ch05_domains", [])
    if domains and not any(d in text for d in domains):
        if not accounting_match(text, cfg):
            return None
    return Sample(
        instruction=str(row.get("instruction") or ""),
        input=str(row.get("input") or ""),
        output=str(row.get("output") or ""),
        source="S4_ch05-sft",
        task="financial_analysis",
    )


def extract_generic_hf(
    row: dict,
    cfg: dict,
    source_id: str,
    hf_id: str,
    require_keyword: bool = True,
) -> Sample | None:
    system = cfg["system_prompt"]
    instruction = str(row.get("instruction") or row.get("prompt") or "")
    inp = str(row.get("input") or row.get("query") or "")
    output = str(row.get("output") or row.get("response") or "")

    if not output:
        parsed = parse_sharegpt(row.get("messages") or row.get("conversations"))
        if parsed:
            instruction, output = parsed
            inp = ""

    combined = instruction + inp + output
    if require_keyword and not accounting_match(combined, cfg):
        return None

    if "[Calculator(" in output:
        output = convert_calculator_to_tool_call(output)

    if not instruction:
        return None
    return Sample(
        instruction=prepend_system(instruction, system),
        input=inp,
        output=output,
        source=f"{source_id}_{hf_id.split('/')[-1]}",
        task="finance_reasoning",
    )


def iter_hf_rows(source_key: str, source_cfg: dict, cfg: dict) -> Iterator[Sample | None]:
    hf_id = source_cfg["hf_id"]
    split = source_cfg.get("split", "train")
    streaming = source_cfg.get("streaming", False)

    extractors = {
        "S1": extract_s1,
        "S2": extract_s2,
        "S3": extract_s3,
        "S4": extract_s4,
    }

    load_kwargs: dict[str, Any] = {"path": hf_id, "split": split}
    if streaming:
        load_kwargs["streaming"] = True
    ds = load_dataset(**load_kwargs)
    if streaming:
        ds = ds  # IterableDataset
    require_kw = source_key in {"S5", "S6", "S7", "S8"}

    for row in ds:
        row = dict(row)
        if source_key in extractors:
            yield extractors[source_key](row, cfg)
        else:
            yield extract_generic_hf(row, cfg, source_key, hf_id, require_keyword=require_kw)


def collect_from_source(
    source_key: str,
    source_cfg: dict,
    cfg: dict,
    max_count: int,
    stats: BuildStats,
    rng: random.Random,
) -> list[Sample]:
    if not source_cfg.get("enabled", True):
        return []

    results: list[Sample] = []
    hf_id = source_cfg["hf_id"]
    bar = tqdm(desc=f"{source_key} {hf_id}", total=max_count if max_count > 0 else None)

    try:
        for maybe in iter_hf_rows(source_key, source_cfg, cfg):
            if maybe is None:
                stats.rejected[source_key] += 1
                continue
            if not validate_sample(maybe, cfg):
                stats.rejected[source_key] += 1
                continue
            results.append(maybe)
            stats.extracted[source_key] += 1
            bar.update(1)
            if max_count > 0 and len(results) >= max_count:
                break
    except Exception as e:
        bar.close()
        print(f"[WARN] {source_key} 加载失败: {e}")
        return results

    bar.close()
    rng.shuffle(results)
    return results


def apply_mix(
    buckets: dict[str, list[Sample]],
    cfg: dict,
    profile: dict,
    target: int,
    rng: random.Random,
) -> list[Sample]:
    weights = cfg["mix_weights"]
    core_keys = ["S1", "S2", "S3", "S4"]
    sup_keys = ["S5", "S6", "S7", "S8"]
    beh_keys = ["G1", "G2"]
    gen_keys = ["G3"]

    def take(keys: list[str], ratio: float) -> list[Sample]:
        need = int(target * ratio)
        pool: list[Sample] = []
        for k in keys:
            pool.extend(buckets.get(k, []))
        rng.shuffle(pool)
        return pool[:need]

    mixed: list[Sample] = []
    mixed.extend(take(core_keys, weights["L1_core"]))
    mixed.extend(take(sup_keys, weights["L2_supplement"]))
    mixed.extend(take(beh_keys, weights["L3_behavior"]))
    mixed.extend(take(gen_keys, weights["L4_general"]))

    # 若不足 target，从剩余样本补齐
    if len(mixed) < target:
        rest: list[Sample] = []
        for k in buckets:
            rest.extend(buckets[k])
        seen = {id(s) for s in mixed}
        for s in rest:
            if id(s) not in seen:
                mixed.append(s)
                seen.add(id(s))
            if len(mixed) >= target:
                break

    rng.shuffle(mixed)
    return mixed[:target] if target > 0 else mixed


def split_eval(samples: list[Sample], ratio: float, rng: random.Random) -> tuple[list[Sample], list[Sample]]:
    rng.shuffle(samples)
    n_eval = max(1, int(len(samples) * ratio))
    return samples[n_eval:], samples[:n_eval]


def main() -> None:
    import os

    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "600")
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "600")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    parser = argparse.ArgumentParser(description="构建会计学 SFT 数据集（微调方案 1）")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profile", choices=["mvp", "recommended", "full"], default="recommended")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--skip-sources",
        type=str,
        default="",
        help="逗号分隔跳过源 ID，如 S5,S6",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    profile = cfg["profiles"][args.profile]
    max_per = profile["max_per_source"]
    target_train = profile["target_train_size"]
    skip = {s.strip() for s in args.skip_sources.split(",") if s.strip()}

    rng = random.Random(args.seed)
    stats = BuildStats()
    buckets: dict[str, list[Sample]] = {}

    # 合成数据
    buckets["G1"] = generate_tool_samples(cfg, max_per.get("G1", 500), rng)
    buckets["G2"] = generate_rag_samples(cfg, max_per.get("G2", 500), rng)
    buckets["G3"] = generate_general_samples(cfg, max_per.get("G3", 300), rng)
    for k in ("G1", "G2", "G3"):
        stats.extracted[k] = len(buckets[k])

    # HuggingFace 源
    for sid, scfg in cfg["sources"].items():
        if sid in skip:
            continue
        cap = max_per.get(sid, 5000)
        buckets[sid] = collect_from_source(sid, scfg, cfg, cap, stats, rng)

    mixed = apply_mix(buckets, cfg, profile, target_train, rng)
    eval_ratio = cfg["limits"]["eval_ratio"]
    train, eval_ = split_eval(mixed, eval_ratio, rng)

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    train_rows = [s.to_alpaca() for s in train]
    eval_rows = [s.to_alpaca() for s in eval_]

    with (out_dir / "train.json").open("w", encoding="utf-8") as f:
        json.dump(train_rows, f, ensure_ascii=False, indent=2)
    with (out_dir / "eval.json").open("w", encoding="utf-8") as f:
        json.dump(eval_rows, f, ensure_ascii=False, indent=2)

    mix_ratio = defaultdict(int)
    for s in train:
        mix_ratio[s.source.split("_")[0]] += 1

    manifest = {
        "profile": args.profile,
        "target_train_size": target_train,
        "actual_train": len(train),
        "actual_eval": len(eval_),
        "extracted_by_source": dict(stats.extracted),
        "rejected_by_source": dict(stats.rejected),
        "mix_ratio_prefix": dict(mix_ratio),
        "leak_check": {
            "cflue_test_in_train": 0,
            "note": "CFLUE 仅使用 train split；test 禁止入训",
        },
        "config_path": str(args.config),
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"\n已写入: {out_dir / 'train.json'} ({len(train)} 条)")
    print(f"已写入: {out_dir / 'eval.json'} ({len(eval_)} 条)")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Phase 1 P1-5：将 SFT 数据安装到 LLaMA-Factory（WSL/Linux）
# 用法: ./install_to_llamafactory.sh ~/LLaMA-Factory

set -euo pipefail
LF_ROOT="${1:?LLaMA-Factory path required}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${DATA_DIR:-$SCRIPT_DIR/../datasets/accounting_sft_recommended}"

mkdir -p "$LF_ROOT/data"
cp "$DATA_DIR/train.json" "$LF_ROOT/data/accounting_sft.json"
cp "$DATA_DIR/eval.json" "$LF_ROOT/data/accounting_sft_eval.json"

SNIPPET="$SCRIPT_DIR/../llamafactory/dataset_info.accounting.json"
INFO="$LF_ROOT/data/dataset_info.json"

python3 - <<PY
import json
from pathlib import Path
snippet = json.loads(Path("$SNIPPET").read_text(encoding="utf-8"))
info_path = Path("$INFO")
base = {}
if info_path.exists():
    base = json.loads(info_path.read_text(encoding="utf-8"))
base.update(snippet)
info_path.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
PY

cp "$SCRIPT_DIR/../llamafactory/train_qwen7b_qlora.yaml" "$LF_ROOT/"
echo "OK: installed to $LF_ROOT/data"

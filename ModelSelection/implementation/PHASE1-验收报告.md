# Phase 1 验收报告

**执行日期**：2026-07-31  
**执行环境**：Windows + Python 3.13，`HF_ENDPOINT=https://hf-mirror.com`  
**主产出目录**：`datasets/accounting_sft_recommended/`

---

## 1. 任务完成情况

| 任务 ID | 内容 | 状态 | 证据 |
|---------|------|:----:|------|
| P1-1 | MVP 构建 | ✅ | `accounting_sft_mvp/train.json` **3800** 条 |
| P1-2 | 质量抽检 | ✅ | `phase1_validation.json` 全量类别覆盖 |
| P1-3 | CFLUE 无泄露 | ✅ | `leak_check.cflue_test_in_train = 0` |
| P1-4 | Recommended 构建 | ✅ | `train.json` **11400** 条（目标 12k，eval 600） |
| P1-5 | LLaMA-Factory 注册 | ✅ | `llamafactory/data/` + `dataset_info.json` |

---

## 2. 数据源抽取统计（Recommended）

| 源 | HF 数据集 | 抽取成功 | 拒绝/过滤 | 进入 train 混合 |
|----|-----------|----------|-----------|---------------|
| S1 | lxl3129/sft-audit_regulation | 28,183 | 2,086 | 5,330 |
| S2 | XIANGFENGLI/ACCOUNTING_DATABASES | 1,999 | 2 | 380 |
| S3 | DianJin/CFLUE（CPA/会计筛） | 4,804 | 26,103 | 896 |
| S4 | realrick/ch05-sft-dataset | 1,090 | 5,198 | 232 |
| S7 | DianJin/DianJin-R1-Data | 4,000 | 8,073 | 2,490 |
| G1 | 合成工具调用 | 1,200 | — | 819 |
| G2 | 合成 RAG+citation | 1,200 | — | 687 |
| G3 | 合成通用/拒答 | 600 | — | 566 |

**合计 train**：11,400 + **eval**：600

### 2.1 本次跳过的源（网络超时）

| 源 | 原因 | 后续补全命令 |
|----|------|--------------|
| S5 ODA-Fin-SFT-318k | `train.json` 大文件下载超时 | 稳定网络后去掉 `--skip-sources` 中的 S5 |
| S6 Agentar-DeepFinance-100K | 同上 | 同上 |
| S8 BAAI IndustryInstruction | 同上 | 同上 |

补全命令：

```powershell
$env:HF_ENDPOINT="https://hf-mirror.com"
python scripts/build_accounting_sft.py `
  --output-dir datasets/accounting_sft_full `
  --profile full `
  --seed 42
# 不传 --skip-sources
```

---

## 3. 混合比例（Recommended train）

| 前缀 | 条数 | 占比 |
|------|------|------|
| S1 审计 | 5,330 | 46.8% |
| S7 金融推理 | 2,490 | 21.8% |
| S3 CPA/会计 | 896 | 7.9% |
| G1 工具 | 819 | 7.2% |
| G2 RAG | 687 | 6.0% |
| G3 通用 | 566 | 5.0% |
| S2 准则库 | 380 | 3.3% |
| S4 财务分析 | 232 | 2.0% |

审计占比偏高但在可接受范围；进入 Phase 2 前可按 02a §5 再降 S1 权重（换 profile 或调 `mix_weights`）。

---

## 4. 质量验收（P1-2 / P1-3）

- Alpaca 格式：`instruction` / `input` / `output` 100% 合规  
- 中文占比：低中文样本 **0**  
- 全量类别：`audit` / `accounting_std` / `calculation` / `tool` / `rag` / `other` 均存在  
- 泄露检查：仅使用 CFLUE **train** split  

抽检样例见：`sample_preview.json`（6 类各 1 条）

---

## 5. LLaMA-Factory 接入（P1-5）

已生成本地 bundle：

```text
llamafactory/
├── data/
│   ├── accounting_sft.json      ← 来自 recommended/train.json
│   ├── accounting_sft_eval.json
│   └── dataset_info.json
└── train_qwen7b_qlora.yaml
```

安装到本机 LLaMA-Factory：

```powershell
.\scripts\install_to_llamafactory.ps1 -LlamafactoryRoot "D:\LLaMA-Factory"
```

WSL：

```bash
./scripts/install_to_llamafactory.sh ~/LLaMA-Factory
```

---

## 6. 一键复现

```powershell
cd ModelSelection/implementation/scripts
.\run_phase1.ps1
python validate_phase1.py --data-dir ../datasets/accounting_sft_recommended
```

---

## 7. Phase 2 入口

数据已就绪，下一步：

**[02-Qwen7B微调指南](./02-Qwen7B微调指南.md)** → `llamafactory-cli train train_qwen7b_qlora.yaml`

---

## 8. 验收签字清单

- [x] P1-1 MVP ≥3000  
- [x] P1-2 质量抽检通过  
- [x] P1-3 无 CFLUE test 泄露  
- [x] P1-4 Recommended 8k～15k（11,400）  
- [x] P1-5 LLaMA-Factory 注册文件就绪  
- [ ] S5/S6/S8 待网络稳定后补全（可选增强）

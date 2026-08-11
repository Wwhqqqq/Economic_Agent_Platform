# 02 — Qwen 7B 微调指南



## 1. 本步目标



使用 **QLoRA** 在本地 **5080 16G** 上微调 **Qwen2.5-7B-Instruct**，得到：



- LoRA 适配器目录 `qwen7b-accounting-lora/`，或  

- 合并后的完整权重（可选，便于部署）  



微调聚焦：**会计学审阅话术、工具调用格式、RAG 引用风格**，而非灌输全部准则原文（准则走知识库 RAG）。



> **数据从哪来？** 请先完成 **[02a-微调方案1-数据集构建与实践路线](./02a-微调方案1-数据集构建与实践路线.md)**，运行 `scripts/build_accounting_sft.py` 生成 `train.json` / `eval.json`。



---



## 2. 训练数据（方案 1 摘要）



### 2.1 构建命令



```bash

cd ModelSelection/implementation/scripts

pip install -r requirements-sft-build.txt



python build_accounting_sft.py \

  --output-dir ~/datasets/accounting_sft \

  --profile recommended \

  --seed 42

```



| profile | train 目标规模 | 适用 |

|---------|----------------|------|

| `mvp` | ~4,000 | 首次跑通 QLoRA |

| `recommended` | ~12,000 | **正式上线推荐** |

| `full` | ~30,000 | S1 审计全量 + 补充（注意过拟合） |



### 2.2 混合比例（脚本自动执行）



| 层级 | 来源 | 占比 |

|------|------|------|

| L1 核心 | 审计 S1、准则 S2、CFLUE S3、ch05 S4 | 60% |

| L2 补充 | ODA / DeepFinance / DianJin-R1 / BAAI S5～S8 | 22% |

| L3 行为 | 工具 G1、RAG G2 | 12% |

| L4 通用 | 拒答 G3 | 6% |



详细源清单、字段映射、开发任务 ID 见 **[02a](./02a-微调方案1-数据集构建与实践路线.md)**。



### 2.3 单条样本格式（Alpaca）



```json

{

  "instruction": "你是一名财务审阅助手。请根据提供的上下文分析毛利率变动。",

  "input": "【检索上下文】\n公司 A 2024 年毛利率 32%，2023 年 28%…",

  "output": "根据上下文，毛利率上升 4 个百分点…\n\n**参考来源**：doc_xxx chunk_2"

}

```



含工具调用时，output 使用平台对齐格式：



```text

<tool_call>{"name":"calculator","arguments":{"expression":"1200/800"}}</tool_call>

```



---



## 3. LLaMA-Factory 配置



### 3.1 目录结构



```text

~/LLaMA-Factory/

├── data/

│   ├── accounting_sft.json       ← 来自 build 脚本的 train.json

│   └── accounting_sft_eval.json  ← eval.json（可选单独注册）

└── saves/

    └── qwen7b-accounting-lora/

```



在 `data/dataset_info.json` 注册：



```json

{

  "accounting_sft": {

    "file_name": "accounting_sft.json",

    "formatting": "alpaca",

    "columns": {

      "prompt": "instruction",

      "query": "input",

      "response": "output"

    }

  }

}

```



复制数据：



```bash

cp ~/datasets/accounting_sft/train.json ~/LLaMA-Factory/data/accounting_sft.json

cp ~/datasets/accounting_sft/eval.json   ~/LLaMA-Factory/data/accounting_sft_eval.json

```



### 3.2 QLoRA 训练参数（5080 16G 参考）



创建 `train_qwen7b_qlora.yaml`：



```yaml

### model

model_name_or_path: /mnt/e/models/Qwen2.5-7B-Instruct

quantization_bit: 4

template: qwen



### method

stage: sft

do_train: true

finetuning_type: lora

lora_rank: 16

lora_alpha: 32

lora_target: all



### dataset

dataset: accounting_sft

cutoff_len: 4096

max_samples: 100000

overwrite_cache: true

preprocessing_num_workers: 4



### output

output_dir: /mnt/e/models/qwen7b-accounting-lora

logging_steps: 10

save_steps: 200

plot_loss: true

overwrite_output_dir: true



### train

per_device_train_batch_size: 2

gradient_accumulation_steps: 8

learning_rate: 1.0e-4

num_train_epochs: 3

lr_scheduler_type: cosine

warmup_ratio: 0.1

bf16: true

ddp_timeout: 180000000



### eval

val_size: 0.05

per_device_eval_batch_size: 1

eval_strategy: steps

eval_steps: 200

```



> `recommended` 规模（~12k）建议 `num_train_epochs: 2～3`；`full` 可降至 `1～2` 防过拟合。



### 3.3 启动训练



```bash

cd ~/LLaMA-Factory

source ~/venv/agent-train/bin/activate

llamafactory-cli train train_qwen7b_qlora.yaml

```



**监控**：loss 应平稳下降；`eval_loss` 不应长期远高于 train（过拟合信号）。



### 3.4 合并权重（可选）



若 vLLM 不便加载 LoRA，可合并：



```bash

llamafactory-cli export \

  --model_name_or_path /mnt/e/models/Qwen2.5-7B-Instruct \

  --adapter_name_or_path /mnt/e/models/qwen7b-accounting-lora \

  --template qwen \

  --export_dir /mnt/e/models/Qwen2.5-7B-Instruct-Accounting-Merged \

  --export_size 2 \

  --export_device cpu

```



---



## 4. 微调 vs RAG 边界



| 微调（SFT） | RAG（知识库） |

|-------------|---------------|

| 审阅话术、工具格式、引用写法 | 准则 / 法规原文 |

| CPA 解析**风格**（S3） | 具体客户报表 PDF |

| 审计案例结构（S1） | 可更新条文（只更库） |



---



## 5. 微调后本地验证



```bash

llamafactory-cli chat \

  --model_name_or_path /mnt/e/models/Qwen2.5-7B-Instruct \

  --adapter_name_or_path /mnt/e/models/qwen7b-accounting-lora \

  --template qwen

```



抽检问题：



1. 「请对毛利率下降给出审阅意见」（应结构化、专业）  

2. 「调用 calculator 计算流动比率」（应输出 `<tool_call>`）  

3. 给定【检索上下文】的问题（应含 **参考来源**）  

4. 无关有害请求（应拒答）  



---



## 6. 上传到推理机



```bash

tar -czvf qwen7b-accounting-lora.tar.gz -C /mnt/e/models qwen7b-accounting-lora

scp qwen7b-accounting-lora.tar.gz root@<GPU_IP>:/opt/models/

```



---



## 7. 本步验收清单



- [ ] `02a`：`build_accounting_sft.py` 产出 `train.json`，`manifest.json` 各源非 0  

- [ ] `train.json` ≥500 条（MVP）或 ≥8000 条（推荐）  

- [ ] QLoRA 训练完成，`adapter_config.json` 存在  

- [ ] 本地 chat 抽检 ≥10 条满意  

- [ ] 权重已同步到 GN7 `/opt/models/`  



---



## 8. 下一步



**[03-模型部署与推理服务](./03-模型部署与推理服务.md)** — vLLM 加载 7B + LoRA，部署 PaddleOCR-VL 1.6。


# ModelSelection — 模型选型与实施

本目录存放 **Economic Agent Platform** 的模型选型与落地实施文档。

## 选型结论

| 角色 | 选定模型 |
|------|----------|
| 文本 LLM | **Qwen 7B**（Qwen2.5-7B-Instruct，QLoRA 微调） |
| 文档视觉 | **PaddleOCR-VL 1.6** |

## 文档索引

### 调研

| 文档 | 说明 |
|------|------|
| [模型选型调研报告.md](./模型选型调研报告.md) | 候选模型对比与推荐组合 |

### 实施（按顺序阅读）

| 步骤 | 文档 |
|:----:|------|
| 索引 | [implementation/README.md](./implementation/README.md) |
| 0 | [00-总览与架构.md](./implementation/00-总览与架构.md) |
| 1 | [01-环境准备与模型下载.md](./implementation/01-环境准备与模型下载.md) |
| **2a** | **[02a-微调方案1-数据集构建与实践路线.md](./implementation/02a-微调方案1-数据集构建与实践路线.md)** |
| 2 | [02-Qwen7B微调指南.md](./implementation/02-Qwen7B微调指南.md) |
| 3 | [03-模型部署与推理服务.md](./implementation/03-模型部署与推理服务.md) |
| 4 | [04-平台集成与配置.md](./implementation/04-平台集成与配置.md) |
| 5 | [05-测试验收与上线.md](./implementation/05-测试验收与上线.md) |

### 微调方案 1 脚本

```bash
cd ModelSelection/implementation/scripts
pip install -r requirements-sft-build.txt
python build_accounting_sft.py --output-dir ~/datasets/accounting_sft --profile recommended
```

**更新日期**：2026-07-31

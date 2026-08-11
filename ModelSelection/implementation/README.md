# Qwen 7B + PaddleOCR-VL 1.6 实施文档



**目标**：从模型下载 → **开源数据集构建（方案 1）** → Qwen 7B 微调 → GPU 推理部署 → 接入 Economic Agent Platform。



**选定模型**



| 角色 | 模型 |

|------|------|

| 文本 LLM（微调 + 推理） | **Qwen2.5-7B-Instruct**（或同系列 Qwen3-8B，步骤类似） |

| 文档视觉 | **PaddleOCR-VL 1.6** |



**推荐硬件**



| 阶段 | 机器 |

|------|------|

| 微调 | 本地 Windows + **RTX 5080 16G**（WSL2） |

| 推理 + OCR | 阿里云 **GN7 T4 16G**（8vCPU/32G）或同规格 |

| 平台 + RAG | **4核8G** 轻量（或 GN7 同机 Docker） |



---



## 文档阅读顺序



| 步骤 | 文档 | 产出 |

|:----:|------|------|

| 0 | [00-总览与架构](./00-总览与架构.md) | 全局架构、目录规划、里程碑 |

| 1 | [01-环境准备与模型下载](./01-环境准备与模型下载.md) | CUDA、Python、模型权重就绪 |

| **2a** | **[02a-微调方案1-数据集构建与实践路线](./02a-微调方案1-数据集构建与实践路线.md)** | **`train.json` / `eval.json` / `manifest.json`** |

| **✅** | **[PHASE1-验收报告](./PHASE1-验收报告.md)** | **Phase 1 已完成（train 11,400 条）** |

| **⏳** | **[PHASE2-安装指南](./PHASE2-安装指南.md)** | **Phase 2 环境（国内镜像安装脚本）** |

| 2 | [02-Qwen7B微调指南](./02-Qwen7B微调指南.md) | LoRA 适配器 / 合并权重 |

| 3 | [03-模型部署与推理服务](./03-模型部署与推理服务.md) | vLLM + PaddleOCR-VL 服务 |

| 4 | [04-平台集成与配置](./04-平台集成与配置.md) | `.env`、ingestion、前后端联调 |

| 5 | [05-测试验收与上线](./05-测试验收与上线.md) | 冒烟、RAG、回归、上线清单 |



**预计周期（单人兼职）**：约 2～4 周（含数据构建与联调）。



---



## 微调方案 1 快速入口



```bash

cd ModelSelection/implementation/scripts

pip install -r requirements-sft-build.txt

python build_accounting_sft.py --output-dir ~/datasets/accounting_sft --profile recommended

```



脚本与配置：



| 路径 | 说明 |

|------|------|

| `scripts/build_accounting_sft.py` | 从 8 个 HF 源 + 合成 G1～G3 构建 SFT |

| `scripts/config/dataset_sources.yaml` | 源开关、关键词、profile 规模 |



---



## 与本仓库代码的对应关系



| 平台模块 | 路径 |

|----------|------|

| LLM Provider | `backend/app/core/config.py`、`backend/app/llm/factory.py` |

| Agent 推理 | `backend/app/agent/runtime.py` |

| 工具（SFT 对齐） | `backend/app/tools/builtin/calculator.py`、`file_reader.py`、`accounting/*.py` |

| 媒体 / 图片入库 | `backend/app/ingestion/media/service.py` |

| 知识库 ingest | `backend/app/jobs/tasks.py`、`backend/app/api/knowledge.py` |

| 生产部署 | `deploy/docker-compose.prod.yml`、`deploy/env.production.template` |

| 架构目标 | `docs/architecture/target/05-媒体资产与多模态解析.md` |



---



*文档版本：1.1 | 日期：2026-07-31*


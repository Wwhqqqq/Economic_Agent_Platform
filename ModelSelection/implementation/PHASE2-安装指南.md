# Phase 2 国内镜像安装指南

**当前进度（2026-07-31）**

| 阶段 | 状态 | 说明 |
|------|:----:|------|
| Phase 1 数据集 | ✅ 完成 | train 11,400 条，验收通过 |
| PyTorch cu128 | ✅ 已装 | `2.11.0+cu128`，5080 CUDA 可用 |
| 训练依赖 pip | ⏸ 未完成 | 卡在 `bitsandbytes` 外网下载 |
| LLaMA-Factory | ❌ 未装 | |
| Qwen2.5-7B 权重 | ❌ 未下 | 约 15GB |
| QLoRA 训练 | ❌ 未跑 | 装完后由 Agent 执行 |

> WSL 虚拟磁盘损坏，**改用 Windows 原生 + E 盘**（C 盘空间不足）。

---

## 一键安装（推荐）

PowerShell **以普通用户**打开，执行：

```powershell
cd E:\Desktop\agent-platform\agent-platform\ModelSelection\implementation\scripts\install
Set-ExecutionPolicy -Scope Process Bypass
.\install_phase2_all_cn.ps1
```

预计耗时：**1～3 小时**（主要等 Qwen 15GB 模型下载）。

---

## 分步安装（某步失败可单独重跑）

```powershell
cd E:\Desktop\agent-platform\agent-platform\ModelSelection\implementation\scripts\install

.\01_create_venv.ps1          # 创建 E:\venv\agent-train
.\02_install_pytorch_cn.ps1   # PyTorch cu128（清华/aliyun/官方 镜像回退）
.\03_install_train_deps_cn.ps1 # transformers/peft/bitsandbytes 等（清华 PyPI）
.\04_clone_llamafactory_cn.ps1 # LLaMA-Factory（ghproxy/gitclone 镜像）
.\05_download_qwen_cn.ps1     # Qwen 权重（ModelScope 国内，失败回退 hf-mirror）
.\06_install_sft_data.ps1     # 复制 Phase1 数据 + 训练 yaml
.\verify_phase2_env.ps1       # 验收清单
```

---

## 国内镜像一览

| 用途 | 镜像 |
|------|------|
| pip 通用包 | `https://pypi.tuna.tsinghua.edu.cn/simple` |
| PyTorch cu128 | 清华 → 阿里云 → 官方（脚本自动回退） |
| HuggingFace | `HF_ENDPOINT=https://hf-mirror.com` |
| Qwen 模型 | **ModelScope**（优先）→ hf-mirror（回退） |
| GitHub 克隆 | ghproxy → gitclone → 直连 |

---

## 磁盘与路径规划

| 路径 | 内容 | 约占用 |
|------|------|--------|
| `E:\venv\agent-train` | Python 虚拟环境 | ~5 GB |
| `E:\models\Qwen2.5-7B-Instruct` | 基座模型 | ~15 GB |
| `E:\models\qwen7b-accounting-lora` | LoRA 产出（训练后） | ~200 MB |
| `E:\LLaMA-Factory` | 微调框架 | ~50 MB |

**E 盘建议剩余 ≥ 30 GB**（当前约 203 GB 可用，足够）。

---

## 安装完成验收

运行：

```powershell
.\verify_phase2_env.ps1
```

应全部 `[OK]`（LoRA 一项训练前为 `[FAIL]` 是正常的）。

验收报告写入：`datasets/phase2_env_validation.json`

---

## 装完后告诉我

我会自动继续 Phase 2 剩余步骤：

1. **P2-1** QLoRA 训练（11,400 样本 × 2 epoch）
2. **P2-2～P2-4** 10 题抽检 + CPA/工具格式验证
3. **P2-5** 打包 LoRA → GN7 部署包
4. 生成 **PHASE2-验收报告.md**

你只需回复：**「环境装好了」** 或贴 `verify_phase2_env.ps1` 的输出即可。

---

## 常见问题

### bitsandbytes 下载慢/断线

单独重跑第 3 步（已加 600s timeout + 10 次重试）：

```powershell
.\03_install_train_deps_cn.ps1
```

### PyTorch 检测不到 5080

必须用 **cu128**，不能用 cu124/cu126。重跑：

```powershell
.\02_install_pytorch_cn.ps1
```

### ModelScope 下载 Qwen 失败

脚本会自动回退 hf-mirror；也可手动：

```powershell
$env:HF_ENDPOINT="https://hf-mirror.com"
E:\venv\agent-train\Scripts\python.exe -m pip install modelscope huggingface_hub
E:\venv\agent-train\Scripts\python.exe ..\download_qwen_modelscope.py --local-dir E:\models\Qwen2.5-7B-Instruct
```

### 已有半截 venv

可删除后重装：

```powershell
Remove-Item -Recurse -Force E:\venv\agent-train
.\install_phase2_all_cn.ps1
```

或从失败步骤继续（PyTorch 已装好则跳过 02）。

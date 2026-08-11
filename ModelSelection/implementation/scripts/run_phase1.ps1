# Phase 1 一键执行（PowerShell）
# 用法: .\run_phase1.ps1

$ErrorActionPreference = "Stop"
$ScriptRoot = $PSScriptRoot
$ImplRoot = Split-Path $ScriptRoot -Parent
$DatasetsRoot = Join-Path $ImplRoot "datasets"

$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HF_HUB_DOWNLOAD_TIMEOUT = "600"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

Write-Host "=== Phase 1 P1-1: MVP build ===" -ForegroundColor Cyan
python (Join-Path $ScriptRoot "build_accounting_sft.py") `
  --output-dir (Join-Path $DatasetsRoot "accounting_sft_mvp") `
  --profile mvp `
  --seed 42 `
  --skip-sources "S5,S6,S8"

Write-Host "=== Phase 1 P1-4: Recommended build ===" -ForegroundColor Cyan
python (Join-Path $ScriptRoot "build_accounting_sft.py") `
  --output-dir (Join-Path $DatasetsRoot "accounting_sft_recommended") `
  --profile recommended `
  --seed 42 `
  --skip-sources "S5,S6,S8"

Write-Host "=== Phase 1 P1-2/P1-3: Validation ===" -ForegroundColor Cyan
python (Join-Path $ScriptRoot "validate_phase1.py") `
  --data-dir (Join-Path $DatasetsRoot "accounting_sft_mvp")
python (Join-Path $ScriptRoot "validate_phase1.py") `
  --data-dir (Join-Path $DatasetsRoot "accounting_sft_recommended")

Write-Host "=== Phase 1 P1-5: Local LLaMA-Factory data bundle ===" -ForegroundColor Cyan
$LfBundle = Join-Path $ImplRoot "llamafactory\data"
New-Item -ItemType Directory -Force -Path $LfBundle | Out-Null
Copy-Item (Join-Path $DatasetsRoot "accounting_sft_recommended\train.json") (Join-Path $LfBundle "accounting_sft.json") -Force
Copy-Item (Join-Path $DatasetsRoot "accounting_sft_recommended\eval.json") (Join-Path $LfBundle "accounting_sft_eval.json") -Force
Copy-Item (Join-Path $ImplRoot "llamafactory\dataset_info.accounting.json") (Join-Path $LfBundle "dataset_info.json") -Force

Write-Host "Phase 1 complete. See datasets/accounting_sft_recommended/ and PHASE1-验收报告.md" -ForegroundColor Green

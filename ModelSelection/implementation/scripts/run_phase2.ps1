# Phase 2 一键：验收 Phase1 → 训练 → 验证 → 打包
param(
    [switch]$SkipEnvSetup,
    [switch]$SkipTraining,
    [switch]$SkipInference,
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train"
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$ImplRoot = Join-Path $ScriptDir ".."
$LoraDir = Join-Path $ModelsRoot "qwen7b-accounting-lora"
$py = Join-Path $VenvRoot "Scripts\python.exe"

Write-Host "=== Phase 2 全流程 ===" -ForegroundColor Cyan

# Phase 1 门禁
Write-Host "[Gate] Phase 1 验收 ..."
& python (Join-Path $ScriptDir "validate_phase1.py") `
    --data-dir (Join-Path $ImplRoot "datasets\accounting_sft_recommended")
if ($LASTEXITCODE -ne 0) { throw "Phase 1 未通过，中止 Phase 2" }

if (-not $SkipEnvSetup) {
    & (Join-Path $ScriptDir "setup_phase2_env.ps1") `
        -ModelsRoot $ModelsRoot `
        -LlamafactoryRoot $LlamafactoryRoot `
        -VenvRoot $VenvRoot
}

if (-not $SkipTraining) {
    Write-Host "[P2-1] 启动 QLoRA 训练 ..." -ForegroundColor Yellow
    $env:PYTHONUTF8 = "1"
    Push-Location $LlamafactoryRoot
    & (Join-Path $VenvRoot "Scripts\llamafactory-cli.exe") train train_qwen7b_qlora.yaml
    $trainExit = $LASTEXITCODE
    Pop-Location
    if ($trainExit -ne 0) { throw "训练失败 exit=$trainExit" }
}

# 验证
Write-Host "[P2-2~P2-4] Phase 2 验证 ..." -ForegroundColor Yellow
$validateArgs = @(
    (Join-Path $ScriptDir "validate_phase2.py"),
    "--lora-dir", $LoraDir,
    "--base-model", (Join-Path $ModelsRoot "Qwen2.5-7B-Instruct")
)
if (-not $SkipInference) { $validateArgs += "--run-inference" }
& $py @validateArgs
if ($LASTEXITCODE -ne 0) { Write-Warning "部分验证未通过，请查看 phase2_validation.json" }

# 打包
Write-Host "[P2-5] 打包 LoRA ..." -ForegroundColor Yellow
& (Join-Path $ScriptDir "package_lora.ps1") -LoraDir $LoraDir -OutputDir $ModelsRoot

Write-Host "=== Phase 2 完成 ===" -ForegroundColor Green
Write-Host "LoRA: $LoraDir"
Write-Host "验收: $(Join-Path $LoraDir 'phase2_validation.json')"

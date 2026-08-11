# Phase 2 install (Windows + RTX 5080, CN mirrors)
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File install_phase2_all_cn.ps1

param(
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train",
    [switch]$SkipModelDownload,
    [switch]$SkipLlamafactoryClone
)

$ErrorActionPreference = "Stop"
$InstallDir = $PSScriptRoot

$steps = @(
    @{ Name = "01_create_venv"; Script = "01_create_venv.ps1"; Skip = $false },
    @{ Name = "02_install_pytorch_cn"; Script = "02_install_pytorch_cn.ps1"; Skip = $false },
    @{ Name = "03_install_train_deps_cn"; Script = "03_install_train_deps_cn.ps1"; Skip = $false },
    @{ Name = "04_clone_llamafactory_cn"; Script = "04_clone_llamafactory_cn.ps1"; Skip = $SkipLlamafactoryClone },
    @{ Name = "05_download_qwen_cn"; Script = "05_download_qwen_cn.ps1"; Skip = $SkipModelDownload },
    @{ Name = "06_install_sft_data"; Script = "06_install_sft_data.ps1"; Skip = $false }
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Phase 2 install (CN mirrors)" -ForegroundColor Cyan
Write-Host " Models: $ModelsRoot" -ForegroundColor Cyan
Write-Host " LLaMA-Factory: $LlamafactoryRoot" -ForegroundColor Cyan
Write-Host " Venv: $VenvRoot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

foreach ($step in $steps) {
    if ($step.Skip) {
        Write-Host "SKIP: $($step.Name)" -ForegroundColor Yellow
        continue
    }
    $scriptPath = Join-Path $InstallDir $step.Script
    Write-Host ""
    Write-Host "RUN: $($step.Name)" -ForegroundColor Green
    & $scriptPath -ModelsRoot $ModelsRoot -LlamafactoryRoot $LlamafactoryRoot -VenvRoot $VenvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $($step.Name) exit=$LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "RUN: verify_phase2_env" -ForegroundColor Green
& (Join-Path $InstallDir "verify_phase2_env.ps1") `
    -ModelsRoot $ModelsRoot `
    -LlamafactoryRoot $LlamafactoryRoot `
    -VenvRoot $VenvRoot `
    -Strict

Write-Host ""
Write-Host "Done. Run verify_phase2_env.ps1 or tell the agent to continue training." -ForegroundColor Green

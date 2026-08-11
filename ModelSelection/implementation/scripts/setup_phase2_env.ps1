# Phase 2 environment setup — delegates to CN mirror installer
# Usage: .\setup_phase2_env.ps1
# Prefer: .\install\install_phase2_all_cn.ps1  (see PHASE2-安装指南.md)

param(
    [switch]$SkipModelDownload,
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train"
)

$installAll = Join-Path $PSScriptRoot "install\install_phase2_all_cn.ps1"
if (-not (Test-Path $installAll)) {
    throw "Missing $installAll — see PHASE2-安装指南.md"
}

$args = @{
    ModelsRoot = $ModelsRoot
    LlamafactoryRoot = $LlamafactoryRoot
    VenvRoot = $VenvRoot
}
if ($SkipModelDownload) { $args.SkipModelDownload = $true }

& $installAll @args
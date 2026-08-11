param(
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

Write-StepHeader "Step 6/6: Install Phase1 SFT data into LLaMA-Factory"

$ImplRoot = Join-Path $Script:ImplScriptsDir ".."
$DataDir = Join-Path $ImplRoot "datasets\accounting_sft_recommended"

if (-not (Test-Path (Join-Path $DataDir "train.json"))) {
    throw "Phase1 train.json missing. Run run_phase1.ps1 first."
}

& (Join-Path $Script:ImplScriptsDir "install_to_llamafactory.ps1") `
    -LlamafactoryRoot $LlamafactoryRoot `
    -DataDir $DataDir

Copy-Item (Join-Path $ImplRoot "llamafactory\train_qwen7b_qlora_windows.yaml") `
    (Join-Path $LlamafactoryRoot "train_qwen7b_qlora.yaml") -Force

$lfData = Join-Path $LlamafactoryRoot "data\accounting_sft.json"
if (-not (Test-Path $lfData)) { throw "Failed to copy accounting_sft.json" }

Write-Host "OK: SFT data registered in $LlamafactoryRoot"

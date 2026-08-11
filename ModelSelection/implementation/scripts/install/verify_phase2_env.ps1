param(
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

Write-StepHeader "Phase 2 Environment Verification"

$modelDir = Join-Path $ModelsRoot "Qwen2.5-7B-Instruct"
$loraDir = Join-Path $ModelsRoot "qwen7b-accounting-lora"
$lfCli = Join-Path $VenvRoot "Scripts\llamafactory-cli.exe"
$ImplRoot = Join-Path $Script:ImplScriptsDir ".."
$dataDir = Join-Path $ImplRoot "datasets\accounting_sft_recommended"

$checks = @()

function Add-Check {
    param([string]$Name, [bool]$Passed, [string]$Detail)
    $script:checks += [PSCustomObject]@{ name = $Name; passed = $Passed; detail = $Detail }
}

# GPU
try {
    $nvidia = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null
    Add-Check "GPU nvidia-smi" ($null -ne $nvidia) ($nvidia -join "; ")
} catch {
    Add-Check "GPU nvidia-smi" $false $_.Exception.Message
}

# venv + torch
if (Test-Path $Script:Py) {
    $torchInfo = & $Script:Py -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')" 2>&1
    $cudaOk = [bool]($torchInfo -match "True")
    Add-Check "PyTorch cu128 + CUDA" $cudaOk (($torchInfo | Out-String).Trim())
} else {
    Add-Check "Python venv" $false "missing $VenvRoot"
}

# deps
if (Test-Path $Script:Py) {
    $depsOk = $true
    $depsDetail = ""
    $oldEa = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Script:Py -c "import transformers, peft, accelerate, bitsandbytes, datasets, modelscope" 2>&1 | Out-Null
    $ErrorActionPreference = $oldEa
    if ($LASTEXITCODE -ne 0) { $depsOk = $false; $depsDetail = "import exit=$LASTEXITCODE" }
    Add-Check "Training deps" $depsOk $depsDetail
}

# LLaMA-Factory (pip install OK; git clone optional)
$lfViaPip = Test-Path $lfCli
Add-Check "LLaMA-Factory (pip/cli)" $lfViaPip $lfCli

# Phase1 data
Add-Check "Phase1 train.json" (Test-Path (Join-Path $dataDir "train.json")) $dataDir
Add-Check "LF accounting_sft.json" (Test-Path (Join-Path $LlamafactoryRoot "data\accounting_sft.json")) $LlamafactoryRoot
Add-Check "train yaml" (Test-Path (Join-Path $LlamafactoryRoot "train_qwen7b_qlora.yaml")) $LlamafactoryRoot

# Base model
$modelOk = (Test-Path (Join-Path $modelDir "config.json")) -and `
    (Get-ChildItem $modelDir -Filter "*.safetensors" -ErrorAction SilentlyContinue)
Add-Check "Qwen2.5-7B-Instruct weights" $modelOk $modelDir

# LoRA (post-training only)
$loraOk = Test-Path (Join-Path $loraDir "adapter_config.json")
Add-Check "LoRA adapter (post-train)" $loraOk "$loraDir (expected empty before training)"

$passed = ($checks | Where-Object { $_.name -notmatch "post-train" -and -not $_.passed }).Count -eq 0
if ($Strict) {
    $passed = ($checks | Where-Object { -not $_.passed }).Count -eq 0
}

$report = @{
    passed = $passed
    checks = $checks
    models_root = $ModelsRoot
    llamafactory_root = $LlamafactoryRoot
    venv_root = $VenvRoot
    next_step = "Tell agent to run: .\run_phase2.ps1 -SkipEnvSetup"
}

$reportPath = Join-Path $ImplRoot "datasets\phase2_env_validation.json"
$report | ConvertTo-Json -Depth 5 | Set-Content $reportPath -Encoding UTF8

Write-Host ""
foreach ($c in $checks) {
    $icon = if ($c.passed) { 'OK' } else { 'FAIL' }
    $color = if ($c.passed) { "Green" } else { "Red" }
    Write-Host ($icon + " " + $c.name + ": " + $c.detail) -ForegroundColor $color
}

Write-Host ""
Write-Host "Report: $reportPath"
if ($passed) {
    Write-Host "Environment READY for QLoRA training." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Environment NOT ready. Fix FAIL items above." -ForegroundColor Red
    exit 1
}

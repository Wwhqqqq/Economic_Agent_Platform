param(
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

Write-StepHeader "Step 3/6: Install training dependencies (Tsinghua PyPI)"

$reqFile = Join-Path $Script:ImplScriptsDir "requirements-phase2-train.txt"
if (-not (Test-Path $reqFile)) { throw "Missing $reqFile" }

# bitsandbytes 体积大、易断线：单独装 + 高 timeout
Write-Host "Installing bitsandbytes first (large wheel) ..."
Invoke-PipCn @("install", "bitsandbytes>=0.45.0,<0.51")

Write-Host "Installing remaining deps ..."
Invoke-PipCn @("install", "-r", $reqFile)

$py = Get-VenvPython
& $py -c "import transformers, peft, accelerate, bitsandbytes, datasets; print('deps OK')"
Write-Host "OK: training dependencies installed"

param(
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1") -VenvRoot $VenvRoot -ModelsRoot $ModelsRoot -LlamafactoryRoot $LlamafactoryRoot

Write-StepHeader "Step 1/6: Create Python venv"

New-Item -ItemType Directory -Force -Path $ModelsRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $VenvRoot) | Out-Null

if (Test-Path $Script:Py) {
    if (Test-VenvHealthy) {
        Write-Host "venv already exists and healthy: $VenvRoot"
    } else {
        Write-Host "Broken venv detected, recreating: $VenvRoot"
        try {
            Reset-VenvDirectory
        } catch {
            Write-Host ""
            Write-Host "Cannot delete venv (python.exe may be in use)." -ForegroundColor Red
            Write-Host "1. Close all terminals / Cursor tasks using E:\venv\agent-train" -ForegroundColor Yellow
            Write-Host "2. Run: powershell -NoProfile -ExecutionPolicy Bypass -File repair_venv.ps1" -ForegroundColor Yellow
            Write-Host "3. Then rerun install_phase2_all_cn.ps1" -ForegroundColor Yellow
            throw
        }
    }
}

if (-not (Test-Path $Script:Py)) {
    Write-Host "Creating venv: $VenvRoot"
    python -m venv $VenvRoot
    if ($LASTEXITCODE -ne 0) { throw "python -m venv failed" }
}

if (-not (Test-VenvHealthy)) { throw "venv still unhealthy after create: $VenvRoot" }

Invoke-PipCn @("install", "-U", "pip", "wheel", "setuptools")
Invoke-Python @("-m", "pip", "--version")
Write-Host "OK: venv ready at $VenvRoot"

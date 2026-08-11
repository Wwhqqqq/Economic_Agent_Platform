# Force-remove broken venv (stops python processes first)
param(
    [string]$VenvRoot = "E:\venv\agent-train"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1") -VenvRoot $VenvRoot

Write-Host "Repair venv: $VenvRoot"
Stop-VenvPythonProcesses

if (Test-Path $VenvRoot) {
    Write-Host "Removing $VenvRoot ..."
    Remove-Item -Recurse -Force $VenvRoot
}

Write-Host "Creating fresh venv ..."
python -m venv $VenvRoot
if ($LASTEXITCODE -ne 0) { throw "python -m venv failed" }

if (-not (Test-VenvHealthy)) { throw "venv unhealthy after repair" }
Write-Host "OK: venv repaired at $VenvRoot"

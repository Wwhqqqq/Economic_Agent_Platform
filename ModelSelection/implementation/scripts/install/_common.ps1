# Shared config for Phase 2 install scripts (dot-source only)
param(
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train"
)

$Script:ModelsRoot = $ModelsRoot
$Script:LlamafactoryRoot = $LlamafactoryRoot
$Script:VenvRoot = $VenvRoot
$Script:Py = Join-Path $VenvRoot "Scripts\python.exe"
$Script:ImplScriptsDir = Split-Path $PSScriptRoot -Parent

$Script:PipIndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple"
$Script:PipTrustedHost = "pypi.tuna.tsinghua.edu.cn"

$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HF_HUB_DOWNLOAD_TIMEOUT = "600"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

function Get-VenvPython {
    if (-not (Test-Path $Script:Py)) {
        throw "venv not found: $Script:VenvRoot. Run 01_create_venv.ps1 first."
    }
    return $Script:Py
}

function Test-VenvHealthy {
    $cfg = Join-Path $Script:VenvRoot "pyvenv.cfg"
    if (-not (Test-Path $cfg)) { return $false }
    if (-not (Test-Path $Script:Py)) { return $false }
    $oldEa = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Script:Py --version *> $null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $oldEa
    return $ok
}

function Stop-VenvPythonProcesses {
    Get-Process -Name "python", "pythonw" -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and ($_.Path -like "$($Script:VenvRoot)*") } |
        ForEach-Object {
            Write-Host "Stopping process: $($_.Path) (pid $($_.Id))"
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    Start-Sleep -Seconds 2
}

function Reset-VenvDirectory {
    Stop-VenvPythonProcesses
    if (Test-Path $Script:VenvRoot) {
        Remove-Item -Recurse -Force $Script:VenvRoot
    }
}

function Invoke-PipCn {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$PipArgs
    )
    $py = Get-VenvPython
    # Use explicit argument array; avoid "-i" (PowerShell may mis-parse it)
    $allArgs = @(
        "-m", "pip",
        "--default-timeout", "600",
        "--retries", "10",
        "--index-url", $Script:PipIndexUrl,
        "--trusted-host", $Script:PipTrustedHost
    ) + $PipArgs
    & $py @allArgs
    if ($LASTEXITCODE -ne 0) { throw "pip failed: $($PipArgs -join ' ')" }
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )
    $py = Get-VenvPython
    & $py @Args
    if ($LASTEXITCODE -ne 0) { throw "python failed: $($Args -join ' ')" }
}

function Write-StepHeader {
    param([string]$Message)
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

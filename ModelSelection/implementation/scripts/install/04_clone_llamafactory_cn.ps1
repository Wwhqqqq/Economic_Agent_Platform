param(
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

Write-StepHeader "Step 4/6: Clone & install LLaMA-Factory"

$gitUrls = @(
    "https://mirror.ghproxy.com/https://github.com/hiyouga/LLaMA-Factory.git",
    "https://gitclone.com/github.com/hiyouga/LLaMA-Factory.git",
    "https://github.com/hiyouga/LLaMA-Factory.git"
)

if (Test-Path (Join-Path $LlamafactoryRoot ".git")) {
    Write-Host "LLaMA-Factory exists, pulling ..."
    Push-Location $LlamafactoryRoot
    git pull --ff-only
    Pop-Location
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path $LlamafactoryRoot) | Out-Null
    $cloned = $false
    foreach ($url in $gitUrls) {
        Write-Host "Trying git clone: $url"
        if (Test-Path $LlamafactoryRoot) { Remove-Item -Recurse -Force $LlamafactoryRoot -ErrorAction SilentlyContinue }
        git clone --depth 1 $url $LlamafactoryRoot
        if ($LASTEXITCODE -eq 0) {
            $cloned = $true
            break
        }
        Write-Warning "Clone failed from $url"
    }
    if (-not $cloned) { throw "LLaMA-Factory clone failed on all mirrors" }
}

Write-Host "Installing LLaMA-Factory (editable) ..."
Invoke-PipCn @("install", "-e", $LlamafactoryRoot)

$lfCli = Join-Path $VenvRoot "Scripts\llamafactory-cli.exe"
if (-not (Test-Path $lfCli)) { throw "llamafactory-cli not found after install" }
& $lfCli version
Write-Host "OK: LLaMA-Factory ready at $LlamafactoryRoot"

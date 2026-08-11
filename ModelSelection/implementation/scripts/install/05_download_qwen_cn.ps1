param(
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

Write-StepHeader "Step 5/6: Download Qwen2.5-7B-Instruct (~15GB, ModelScope CN)"

$modelDir = Join-Path $ModelsRoot "Qwen2.5-7B-Instruct"
$hasConfig = Test-Path (Join-Path $modelDir "config.json")
$hasWeights = Get-ChildItem $modelDir -Filter "*.safetensors" -ErrorAction SilentlyContinue

if ($hasConfig -and $hasWeights) {
    Write-Host "Model already exists: $modelDir"
    exit 0
}

$py = Get-VenvPython
Invoke-PipCn @("install", "-U", "modelscope")

$dlScript = Join-Path $Script:ImplScriptsDir "download_qwen_modelscope.py"
if (-not (Test-Path $dlScript)) { throw "Missing $dlScript" }

Write-Host "Downloading to $modelDir (may take 30-90 min depending on network) ..."
& $py $dlScript --local-dir $modelDir

if (-not (Test-Path (Join-Path $modelDir "config.json"))) {
    throw "Download incomplete: config.json missing in $modelDir"
}
if (-not (Get-ChildItem $modelDir -Filter "*.safetensors" -ErrorAction SilentlyContinue)) {
    throw "Download incomplete: no .safetensors in $modelDir"
}

Write-Host "OK: Qwen2.5-7B-Instruct ready at $modelDir"

param(
    [string]$ModelsRoot = "E:\models",
    [string]$LlamafactoryRoot = "E:\LLaMA-Factory",
    [string]$VenvRoot = "E:\venv\agent-train"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

Write-StepHeader "Step 2/6: Install PyTorch cu128 (5080 requires CUDA 12.8+)"

$py = Get-VenvPython

# 5080 Blackwell 必须用 cu128+；优先清华 PyTorch 镜像，失败则回退官方/aliyun
$torchIndexes = @(
    "https://mirrors.tuna.tsinghua.edu.cn/pytorch-wheels/cu128",
    "https://mirrors.aliyun.com/pytorch-wheels/cu128",
    "https://download.pytorch.org/whl/cu128"
)

$installed = $false
foreach ($index in $torchIndexes) {
    Write-Host "Trying PyTorch index: $index"
    $oldEa = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    Invoke-Python @("-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio") *> $null
    $ErrorActionPreference = $oldEa

    $installArgs = @(
        "-m", "pip", "install",
        "--default-timeout", "600", "--retries", "10",
        "torch", "torchvision", "torchaudio",
        "--index-url", $index
    )
    & $py @installArgs
    if ($LASTEXITCODE -eq 0) {
        $installed = $true
        Write-Host "PyTorch installed from: $index"
        break
    }
    Write-Warning "Failed from $index, trying next mirror..."
}

if (-not $installed) { throw "PyTorch cu128 install failed on all mirrors" }

& $py (Join-Path $Script:ImplScriptsDir "check_cuda.py")
Write-Host "OK: PyTorch + CUDA verified"

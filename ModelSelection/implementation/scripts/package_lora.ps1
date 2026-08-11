# P2-5：打包 LoRA 适配器供 GN7 部署
param(
    [Parameter(Mandatory = $true)]
    [string]$LoraDir,
    [string]$OutputDir = "E:\models",
    [string]$RemoteHost = "root@111.229.87.157",
    [switch]$Upload
)

$ErrorActionPreference = "Stop"
$LoraDir = (Resolve-Path $LoraDir).Path
$baseName = Split-Path $LoraDir -Leaf
$tarPath = Join-Path $OutputDir "$baseName.tar.gz"

if (-not (Test-Path (Join-Path $LoraDir "adapter_config.json"))) {
    throw "LoRA 目录无效: $LoraDir"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Windows 10+ 自带 tar
Push-Location (Split-Path $LoraDir -Parent)
tar -czvf $tarPath $baseName
Pop-Location

$sizeMb = [math]::Round((Get-Item $tarPath).Length / 1MB, 1)
Write-Host "OK: $tarPath ($sizeMb MB)"

$manifest = @{
    package = $tarPath
    size_mb = $sizeMb
    lora_dir = $LoraDir
    remote_target = "/opt/models/"
    scp_command = "scp `"$tarPath`" ${RemoteHost}:/opt/models/"
    unpack_command = "ssh $RemoteHost 'cd /opt/models && tar -xzvf $baseName.tar.gz'"
}
$manifestPath = Join-Path $LoraDir "package_manifest.json"
$manifest | ConvertTo-Json | Set-Content $manifestPath -Encoding UTF8
Write-Host "Manifest: $manifestPath"

if ($Upload) {
    scp $tarPath "${RemoteHost}:/opt/models/"
    Write-Host "已上传到 ${RemoteHost}:/opt/models/"
}

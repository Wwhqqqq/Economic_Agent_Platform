# Phase 1 P1-5：将 SFT 数据安装到 LLaMA-Factory
# 用法:
#   .\install_to_llamafactory.ps1 -LlamafactoryRoot "D:\LLaMA-Factory" -DataDir "..\datasets\accounting_sft_recommended"

param(
    [Parameter(Mandatory = $true)]
    [string]$LlamafactoryRoot,
    [string]$DataDir = "$PSScriptRoot\..\datasets\accounting_sft_recommended"
)

$ErrorActionPreference = "Stop"
$dataPath = Resolve-Path $DataDir
$lfData = Join-Path $LlamafactoryRoot "data"
$lfInfo = Join-Path $lfData "dataset_info.json"

Copy-Item (Join-Path $dataPath "train.json") (Join-Path $lfData "accounting_sft.json") -Force
Copy-Item (Join-Path $dataPath "eval.json") (Join-Path $lfData "accounting_sft_eval.json") -Force

$snippetPath = Join-Path $PSScriptRoot "..\llamafactory\dataset_info.accounting.json"
$snippet = Get-Content $snippetPath -Raw | ConvertFrom-Json

if (Test-Path $lfInfo) {
    $existing = Get-Content $lfInfo -Raw | ConvertFrom-Json
    $existing.PSObject.Properties | ForEach-Object { $snippet | Add-Member -NotePropertyName $_.Name -NotePropertyValue $_.Value -Force }
}
$snippet | ConvertTo-Json -Depth 10 | Set-Content $lfInfo -Encoding UTF8

Copy-Item (Join-Path $PSScriptRoot "..\llamafactory\train_qwen7b_qlora.yaml") $LlamafactoryRoot -Force

Write-Host "OK: accounting_sft.json + dataset_info 已写入 $lfData"
Write-Host "下一步: cd $LlamafactoryRoot && llamafactory-cli train train_qwen7b_qlora.yaml"

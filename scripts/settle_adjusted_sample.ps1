$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot
$env:PYTHONPATH = "src"

if (-not (Test-Path "reports/adjustments/adjusted_predictions.csv")) {
  throw "Adjusted prediction file not found. Run scripts/adjust_sample.ps1 first."
}

Write-Host "=== Run adjusted sample settlement ==="

python -m sporttery_national.cli settle `
  --predictions reports/adjustments/adjusted_predictions.csv `
  --results data/raw/results/sample_results.csv `
  --output reports/settlements_adjusted

Write-Host "`n=== Adjusted settlement files ==="
Get-ChildItem reports/settlements_adjusted | Sort-Object LastWriteTime -Descending | Select-Object -First 10

Write-Host "`n=== Done ==="

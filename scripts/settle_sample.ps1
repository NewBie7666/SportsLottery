$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot
$env:PYTHONPATH = "src"

if (-not (Test-Path "reports/predictions/predictions.csv")) {
  throw "Prediction file not found. Run scripts/predict_sample.ps1 first."
}

Write-Host "=== Run sample settlement ==="

python -m sporttery_national.cli settle `
  --predictions reports/predictions/predictions.csv `
  --results data/raw/results/sample_results.csv `
  --output reports/settlements

Write-Host "`n=== Settlement files ==="
Get-ChildItem reports/settlements | Sort-Object LastWriteTime -Descending | Select-Object -First 10

Write-Host "`n=== Done ==="

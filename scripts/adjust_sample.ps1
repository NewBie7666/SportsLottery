$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot
$env:PYTHONPATH = "src"

if (-not (Test-Path "reports/predictions/predictions.csv")) {
  throw "Prediction file not found. Run scripts/predict_sample.ps1 first."
}

Write-Host "=== Run sample adjustment experiment ==="

python -m sporttery_national.cli adjust `
  --predictions reports/predictions/predictions.csv `
  --params configs/adjustment/sample_params.json `
  --output reports/adjustments

Write-Host "`n=== Adjustment files ==="
Get-ChildItem reports/adjustments | Sort-Object LastWriteTime -Descending | Select-Object -First 10

Write-Host "`n=== Done ==="

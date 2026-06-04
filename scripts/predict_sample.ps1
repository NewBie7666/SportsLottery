$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot
$env:PYTHONPATH = "src"

if (-not (Test-Path "models/national/elo_state.json")) {
  throw "Model state not found. Run scripts/smoke_test_v1.ps1 first."
}

Write-Host "=== Run sample issue prediction ==="

python -m sporttery_national.cli predict `
  --fixtures data/raw/lottery_fixtures/sample_issue.csv `
  --model-dir models/national `
  --output reports/predictions

Write-Host "`n=== Prediction files ==="
Get-ChildItem reports/predictions | Sort-Object LastWriteTime -Descending | Select-Object -First 10

Write-Host "`n=== Done ==="

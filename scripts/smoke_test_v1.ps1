$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot
$env:PYTHONPATH = "src"

Write-Host "=== SportsLottery National V1 Smoke Test ==="

Write-Host "`n[1/7] Python version"
python --version

Write-Host "`n[2/7] Run unittest"
python -m unittest discover -s tests -v

Write-Host "`n[3/7] Compile source and tests"
python -m compileall src tests

Write-Host "`n[4/7] Fetch / update OpenFootball history"
python -m sporttery_national.cli fetch-history `
  --source openfootball `
  --output data/raw/internationals/openfootball-internationals

Write-Host "`n[5/7] Import history"
python -m sporttery_national.cli import-history `
  --source openfootball `
  --input data/raw/internationals/openfootball-internationals `
  --output data/processed/national_matches.jsonl

Write-Host "`n[6/7] Train model"
python -m sporttery_national.cli train `
  --data data/processed/national_matches.jsonl `
  --model-dir models/national

Write-Host "`n[7/7] Backtest"
python -m sporttery_national.cli backtest `
  --data data/processed/national_matches.jsonl `
  --model-dir models/national `
  --output reports/backtests

Write-Host "`n=== Smoke test completed successfully ==="

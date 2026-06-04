$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$TargetRoot = Join-Path $ProjectRoot "apps\web\public\data"
New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null

$Files = @(
  @{ Source = "reports\predictions\predictions.json"; Target = "predictions.json"; Hint = "scripts\predict_sample.ps1" },
  @{ Source = "reports\backtests\backtest_summary.json"; Target = "backtest_summary.json"; Hint = "scripts\smoke_test_v1.ps1" },
  @{ Source = "reports\backtests\backtest_details.json"; Target = "backtest_details.json"; Hint = "scripts\smoke_test_v1.ps1" },
  @{ Source = "reports\settlements\settlement_summary.json"; Target = "settlement_summary.json"; Hint = "scripts\settle_sample.ps1" },
  @{ Source = "reports\settlements\settlements.json"; Target = "settlements.json"; Hint = "scripts\settle_sample.ps1" },
  @{ Source = "reports\adjustments\adjustment_summary.json"; Target = "adjustment_summary.json"; Hint = "scripts\adjust_sample.ps1" },
  @{ Source = "reports\adjustments\adjusted_predictions.json"; Target = "adjusted_predictions.json"; Hint = "scripts\adjust_sample.ps1" },
  @{ Source = "reports\settlements_adjusted\settlement_summary.json"; Target = "settlements_adjusted\settlement_summary.json"; Hint = "scripts\settle_adjusted_sample.ps1" }
)

Write-Host "=== Export web data snapshots ==="

foreach ($File in $Files) {
  $Source = Join-Path $ProjectRoot $File.Source
  $Target = Join-Path $TargetRoot $File.Target
  $TargetDir = Split-Path -Parent $Target
  New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
  if (Test-Path $Source) {
    Copy-Item -Force $Source $Target
    Write-Host "Copied $($File.Source) -> apps\web\public\data\$($File.Target)"
  } else {
    Write-Warning "Missing $($File.Source). Run $($File.Hint) if this section needs data."
  }
}

Write-Host "`n=== Web data files ==="
Get-ChildItem $TargetRoot -Recurse -File | Sort-Object FullName | Select-Object FullName, Length
Write-Host "`n=== Done ==="

$ErrorActionPreference = "Stop"

$latest = Get-ChildItem "data/reports/local_crypto_autoloop_*" -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latest) {
    Write-Host "No local `$10 AutoLoop reports found yet."
    exit 0
}

$json = Get-ChildItem $latest.FullName -Filter "*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $json) {
    Write-Host "Latest loop folder: $($latest.FullName)"
    Write-Host "No summary JSON found."
    exit 0
}

$summary = Get-Content $json.FullName -Raw | ConvertFrom-Json
$best = $summary.best_round

Write-Host "============================================================"
Write-Host "`$10 Crypto Progress"
Write-Host "============================================================"
Write-Host "Loop summary: $($json.FullName)"
Write-Host "Rounds completed: $($summary.iterations_completed)"
Write-Host ("Initial capital: `$" + ([double]$summary.initial_capital).ToString("0.00"))

if ($best) {
    Write-Host "Best round: $($best.round)"
    Write-Host ("Score: " + ([double]$best.score).ToString("0.0000"))
    Write-Host ("Model balance: `$" + ([double]$best.portfolio_final_model_balance).ToString("0.00"))
    Write-Host ("Buy-hold balance: `$" + ([double]$best.portfolio_final_buyhold_balance).ToString("0.00"))
    Write-Host ("Oracle verification balance: `$" + ([double]$best.portfolio_final_oracle_balance).ToString("0.00"))
    Write-Host ("Avg excess vs buy-hold: " + ([double]$best.avg_excess_vs_buyhold).ToString("0.00%"))
    Write-Host ("Acceptance rate: " + ([double]$best.acceptance_rate).ToString("0.00%"))
    Write-Host "Report: $($best.report_path)"
    Write-Host "Verification dir: $($best.verification_dir)"

    $portfolioPath = Join-Path ([string]$best.verification_dir) "portfolio_daily_verification.csv"
    if (Test-Path $portfolioPath) {
        Write-Host "Portfolio CSV: $portfolioPath"
        $last = Import-Csv $portfolioPath | Select-Object -Last 1
        if ($last) {
            Write-Host "Latest portfolio date: $($last.date)"
            Write-Host ("Latest model total: `$" + ([double]$last.model_total_balance).ToString("0.00"))
            Write-Host ("Latest buy-hold total: `$" + ([double]$last.buyhold_total_balance).ToString("0.00"))
            Write-Host ("Latest oracle total: `$" + ([double]$last.oracle_total_balance).ToString("0.00"))
        }
    }
}

Write-Host "============================================================"

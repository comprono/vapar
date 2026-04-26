param(
    [Parameter(Mandatory = $true)]
    [string]$Root,

    [Parameter(Mandatory = $true)]
    [string]$LogFile,

    [Parameter(Mandatory = $true)]
    [string]$CpuThreads
)

$ErrorActionPreference = "Stop"
Set-Location $Root

$env:PYTHONPATH = $Root
$env:PYTHONUNBUFFERED = "1"
$env:CRYPTO_AUTORESEARCH_WORKERS = $CpuThreads
$env:CRYPTO_FINAL_WALKFORWARD_WORKERS = $CpuThreads
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"

$logDir = Split-Path -Parent $LogFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

& python -u "tests/run_crypto_local_autoloop.py" `
    --years 5 `
    --iterations 999 `
    --time-budget-minutes 240 `
    --month-stride 1 `
    --initial-capital 10 `
    --holdout-new-coins 2>&1 |
    Tee-Object -FilePath $LogFile

exit $LASTEXITCODE

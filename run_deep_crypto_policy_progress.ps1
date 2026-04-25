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
$env:OMP_NUM_THREADS = $CpuThreads
$env:MKL_NUM_THREADS = $CpuThreads
$env:OPENBLAS_NUM_THREADS = $CpuThreads
$env:NUMEXPR_NUM_THREADS = $CpuThreads
$env:PYTHONWARNINGS = "ignore:enable_nested_tensor is True"

$logDir = Split-Path -Parent $LogFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$output = & python -u "tests/run_deep_crypto_policy_walkforward.py" `
    --years 2 `
    --window-size 64 `
    --train-lookback-days 730 `
    --calibration-lookback-days 365 `
    --min-train-samples 384 `
    --max-train-samples 1500 `
    --max-months 4 `
    --pretrain-epochs 2 `
    --epochs 3 `
    --batch-size 128 `
    --d-model 48 `
    --n-heads 4 `
    --n-layers 1 `
    --initial-capital 10 2>&1
$exitCode = $LASTEXITCODE
$output | Tee-Object -FilePath $LogFile

exit $exitCode

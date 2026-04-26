param(
    [string]$ProjectId = $(if ($env:PROJECT_ID) { $env:PROJECT_ID } else { "stellar-shard-376522" }),
    [string]$Zone = $(if ($env:ZONE) { $env:ZONE } else { "us-central1-a" }),
    [string]$InstanceName = $(if ($env:INSTANCE_NAME) { $env:INSTANCE_NAME } else { "deep-policy-trainer-01" }),
    [string]$Branch = $(if ($env:BRANCH) { $env:BRANCH } else { "codex/deep-crypto-colab-training" }),
    [string]$Bucket = $(if ($env:GCS_BUCKET) { $env:GCS_BUCKET } else { "tb1ag-vertex-artifacts-116514064160" }),
    [string]$TrainArgsLine = $env:TRAIN_ARGS_LINE
)

$ErrorActionPreference = "Stop"

if (-not $TrainArgsLine) {
    $TrainArgsLine = "--years 5 --window-size 128 --train-lookback-days 1460 --calibration-lookback-days 365 --min-train-samples 2048 --max-train-samples 30000 --max-months 36 --pretrain-epochs 25 --epochs 35 --batch-size 512 --d-model 128 --n-heads 8 --n-layers 4 --dropout 0.10 --lr 0.0003 --ranking-weight 1.0 --initial-capital 10"
}

Write-Host "== Remote GPU VM training =="
Write-Host "Project:  $ProjectId"
Write-Host "Zone:     $Zone"
Write-Host "Instance: $InstanceName"
Write-Host "Branch:   $Branch"
Write-Host "Bucket:   gs://$Bucket"
Write-Host "Args:     $TrainArgsLine"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$localRunner = Join-Path $repoRoot "infra\gcp\run_on_vm_deep_policy.sh"
if (-not (Test-Path -LiteralPath $localRunner)) {
    throw "Missing local VM runner script: $localRunner"
}

Write-Host "Uploading runner script to VM..."
& gcloud compute scp $localRunner "${InstanceName}:/tmp/run_on_vm_deep_policy.sh" --project $ProjectId --zone $Zone
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upload VM runner script with exit code $LASTEXITCODE."
}

$remoteCommand = @"
set -euo pipefail
export BRANCH='$Branch'
export GCS_BUCKET='$Bucket'
if ! command -v git >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1 || ! command -v pip3 >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git python3 python3-pip curl
fi
chmod +x /tmp/run_on_vm_deep_policy.sh
bash /tmp/run_on_vm_deep_policy.sh $TrainArgsLine
"@

& gcloud compute ssh $InstanceName --project $ProjectId --zone $Zone --command $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "Remote training failed with exit code $LASTEXITCODE."
}

param(
    [string]$ProjectId = $(if ($env:PROJECT_ID) { $env:PROJECT_ID } else { "stellar-shard-376522" }),
    [string]$Zone = $(if ($env:ZONE) { $env:ZONE } else { "us-central1-a" }),
    [string]$InstanceName = $(if ($env:INSTANCE_NAME) { $env:INSTANCE_NAME } else { "deep-policy-trainer-01" }),
    [string]$Branch = $(if ($env:BRANCH) { $env:BRANCH } else { "codex/deep-crypto-colab-training" }),
    [string]$Bucket = $(if ($env:GCS_BUCKET) { $env:GCS_BUCKET } else { "tb1ag-vertex-artifacts-116514064160" }),
    [string]$TrainArgsLine = $env:TRAIN_ARGS_LINE
)

$ErrorActionPreference = "Stop"

function Wait-ForVmSsh {
    param(
        [string]$ProjectId,
        [string]$Zone,
        [string]$InstanceName,
        [int]$TimeoutSeconds = 420
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 8
        & gcloud compute ssh $InstanceName --project $ProjectId --zone $Zone --command "echo vm-ssh-ready" *> $null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }
    return $false
}

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

$runnerUploadPath = Join-Path $env:TEMP ("run_on_vm_deep_policy_{0}.sh" -f ([guid]::NewGuid().ToString("N")))
$remoteCommandPath = Join-Path $env:TEMP ("run_gce_gpu_vm_training_{0}.sh" -f ([guid]::NewGuid().ToString("N")))
$remoteCommand = @"
#!/usr/bin/env bash
set -euo pipefail
echo "[vm-train] remote command started at `$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export BRANCH='$Branch'
export GCS_BUCKET='$Bucket'
if ! command -v git >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1 || ! command -v pip3 >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git python3 python3-pip curl
fi
chmod +x /tmp/run_on_vm_deep_policy.sh
bash /tmp/run_on_vm_deep_policy.sh $TrainArgsLine
echo "[vm-train] remote command finished at `$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"@

$runnerText = Get-Content -Raw -LiteralPath $localRunner
$runnerText = $runnerText -replace "`r`n", "`n"
$runnerText = $runnerText -replace "`r", "`n"
[System.IO.File]::WriteAllText($runnerUploadPath, $runnerText, [System.Text.UTF8Encoding]::new($false))
$remoteCommand = $remoteCommand -replace "`r`n", "`n"
$remoteCommand = $remoteCommand -replace "`r", "`n"
[System.IO.File]::WriteAllText($remoteCommandPath, $remoteCommand, [System.Text.UTF8Encoding]::new($false))
try {
    Write-Host "Uploading runner script to VM..."
    & gcloud compute scp $runnerUploadPath "${InstanceName}:/tmp/run_on_vm_deep_policy.sh" --project $ProjectId --zone $Zone
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upload VM runner script with exit code $LASTEXITCODE."
    }

    Write-Host "Uploading remote command script to VM..."
    & gcloud compute scp $remoteCommandPath "${InstanceName}:/tmp/run_gce_gpu_vm_training.sh" --project $ProjectId --zone $Zone
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upload remote command script with exit code $LASTEXITCODE."
    }

    & gcloud compute ssh $InstanceName --project $ProjectId --zone $Zone --command "bash /tmp/run_gce_gpu_vm_training.sh"
    $firstExit = $LASTEXITCODE
    if ($firstExit -ne 0) {
        Write-Host "Initial SSH run exited with $firstExit. If the VM rebooted for driver install, waiting for SSH and retrying once..."
        $ready = Wait-ForVmSsh -ProjectId $ProjectId -Zone $Zone -InstanceName $InstanceName -TimeoutSeconds 420
        if (-not $ready) {
            throw "Remote training failed with exit code $firstExit and VM did not return to SSH readiness in time."
        }
        & gcloud compute ssh $InstanceName --project $ProjectId --zone $Zone --command "bash /tmp/run_gce_gpu_vm_training.sh"
        if ($LASTEXITCODE -ne 0) {
            throw "Remote training failed after retry with exit code $LASTEXITCODE."
        }
    }
}
finally {
    Remove-Item -LiteralPath $runnerUploadPath -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $remoteCommandPath -ErrorAction SilentlyContinue
}

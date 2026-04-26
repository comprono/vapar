param(
    [string]$ProjectId = $(if ($env:PROJECT_ID) { $env:PROJECT_ID } else { "stellar-shard-376522" }),
    [string]$Zone = $(if ($env:ZONE) { $env:ZONE } else { "us-central1-a" }),
    [string]$InstanceName = $(if ($env:INSTANCE_NAME) { $env:INSTANCE_NAME } else { "deep-policy-trainer-01" }),
    [string]$MachineType = $(if ($env:MACHINE_TYPE) { $env:MACHINE_TYPE } else { "g2-standard-8" }),
    [string]$GpuType = $(if ($env:GPU_TYPE) { $env:GPU_TYPE } else { "nvidia-l4" }),
    [int]$GpuCount = $(if ($env:GPU_COUNT) { [int]$env:GPU_COUNT } else { 1 }),
    [int]$BootDiskGb = $(if ($env:BOOT_DISK_GB) { [int]$env:BOOT_DISK_GB } else { 200 }),
    [string]$ProvisioningModel = $(if ($env:PROVISIONING_MODEL) { $env:PROVISIONING_MODEL } else { "STANDARD" })
)

$ErrorActionPreference = "Stop"

if ($ProjectId -match "^\d+$") {
    throw "ProjectId must be the Google Cloud project ID, not the numeric project number. Use stellar-shard-376522."
}

Write-Host "== Compute Engine GPU VM =="
Write-Host "Project:  $ProjectId"
Write-Host "Zone:     $Zone"
Write-Host "Instance: $InstanceName"
Write-Host "Machine:  $MachineType"
Write-Host "GPU:      $GpuType x$GpuCount"

& gcloud services enable compute.googleapis.com storage.googleapis.com --project $ProjectId | Out-Host

$existingInstance = (& gcloud compute instances list `
    --project $ProjectId `
    --filter "name=($InstanceName) AND zone:($Zone)" `
    --format "value(name)" 2>$null | Select-Object -First 1)
if ($existingInstance) {
    Write-Host "VM already exists. Starting it if needed..."
    & gcloud compute instances start $InstanceName --project $ProjectId --zone $Zone | Out-Host
    exit $LASTEXITCODE
}

$cmd = @(
    "compute","instances","create",$InstanceName,
    "--project",$ProjectId,
    "--zone",$Zone,
    "--machine-type",$MachineType,
    "--accelerator","type=$GpuType,count=$GpuCount",
    "--maintenance-policy","TERMINATE",
    "--restart-on-failure",
    "--provisioning-model",$ProvisioningModel,
    "--boot-disk-size","${BootDiskGb}GB",
    "--boot-disk-type","pd-ssd",
    "--image-family","common-cu128-ubuntu-2204-nvidia-570",
    "--image-project","deeplearning-platform-release",
    "--scopes","https://www.googleapis.com/auth/cloud-platform",
    "--metadata","install-nvidia-driver=True",
    "--tags","deep-policy-trainer"
)

Write-Host "Creating VM..."
& gcloud @cmd
if ($LASTEXITCODE -ne 0) {
    throw "gcloud compute instances create failed with exit code $LASTEXITCODE."
}

Write-Host "VM is ready. SSH command:"
Write-Host "gcloud compute ssh $InstanceName --project $ProjectId --zone $Zone"

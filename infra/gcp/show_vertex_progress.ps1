param(
    [string]$ProjectId = "stellar-shard-376522",
    [string]$Region = "us-central1",
    [string]$Bucket = "tb1ag-vertex-artifacts-116514064160",
    [string]$DisplayName = ""
)

$ErrorActionPreference = "Stop"

Write-Host "== Vertex Jobs =="
& gcloud ai custom-jobs list `
    --project $ProjectId `
    --region $Region `
    --limit 10 `
    --format "table(displayName,state,createTime,name)" | Out-Host

$target = $null
if ($DisplayName) {
    $target = & gcloud ai custom-jobs list `
        --project $ProjectId `
        --region $Region `
        --filter "displayName=$DisplayName" `
        --limit 1 `
        --format "value(name,displayName,state)"
} else {
    $target = & gcloud ai custom-jobs list `
        --project $ProjectId `
        --region $Region `
        --filter "displayName~^deep-policy-" `
        --sort-by "~createTime" `
        --limit 1 `
        --format "value(name,displayName,state)"
}

if (-not $target) {
    Write-Host "`nNo matching Vertex jobs found."
    exit 0
}

$parts = $target -split "\t"
$jobName = $parts[0]
$jobDisplayName = $parts[1]
$jobState = $parts[2]

Write-Host "`nLatest job:"
Write-Host "  displayName: $jobDisplayName"
Write-Host "  state:       $jobState"
Write-Host "  name:        $jobName"

Write-Host "`n== Job Details =="
& gcloud ai custom-jobs describe $jobName --project $ProjectId --region $Region | Out-Host

$runPrefix = "gs://$Bucket/vertex-runs/$jobDisplayName"
Write-Host "`n== Artifact Prefix =="
Write-Host "  $runPrefix"

Write-Host "`n== Remote Files =="
& gcloud storage ls "$runPrefix/**" 2>$null | Out-Host

$logUri = "$runPrefix/logs/deep_policy_train.log"
$tmpDir = Join-Path $env:TEMP "vertex-progress"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
$localLog = Join-Path $tmpDir "$jobDisplayName.log"

& gcloud storage cp $logUri $localLog 2>$null | Out-Null
if (Test-Path $localLog) {
    Write-Host "`n== Log Tail (last 120 lines) =="
    Get-Content $localLog -Tail 120 | Out-Host
} else {
    Write-Host "`nLog not uploaded yet: $logUri"
}


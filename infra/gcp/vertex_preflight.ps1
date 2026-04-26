param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Region,
    [Parameter(Mandatory = $true)][string]$Bucket
)

$ErrorActionPreference = "Stop"

Write-Host "== Vertex preflight =="
Write-Host "Project: $ProjectId"
Write-Host "Region:  $Region"
Write-Host "Bucket:  gs://$Bucket"

Write-Host "`n[1/8] gcloud installed"
& gcloud --version | Out-Host

Write-Host "`n[2/8] active account"
& gcloud auth list --filter=status:ACTIVE --format="value(account)" | Out-Host

Write-Host "`n[3/8] set project"
& gcloud config set project $ProjectId | Out-Host

Write-Host "`n[4/8] required services"
& gcloud services enable aiplatform.googleapis.com storage.googleapis.com --project $ProjectId | Out-Host

Write-Host "`n[5/8] billing status (Cloud Billing API)"
$token = (& gcloud auth print-access-token).Trim()
if (-not $token) {
    throw "Failed to get access token for billing check."
}
$billingUri = "https://cloudbilling.googleapis.com/v1/projects/$ProjectId/billingInfo"
$billing = Invoke-RestMethod -Uri $billingUri -Headers @{ Authorization = "Bearer $token" } -Method Get
$billing | ConvertTo-Json -Depth 5 | Out-Host
if (-not $billing.billingEnabled) {
    throw "Billing is not enabled on project $ProjectId."
}

Write-Host "`n[6/8] bucket access"
& gcloud storage ls ("gs://{0}" -f $Bucket) | Out-Host

Write-Host "`n[7/8] quick Vertex region check"
& gcloud ai custom-jobs list --project $ProjectId --region $Region --limit 1 --format="table(name,state,createTime)" | Out-Host

Write-Host "`n[8/8] GPU quota check ($Region)"
$regionJson = & gcloud compute regions describe $Region --project $ProjectId --format="json"
$regionObj = $regionJson | ConvertFrom-Json
$gpuRows = $regionObj.quotas |
    Where-Object { $_.metric -match "NVIDIA_.*_GPUS" } |
    Sort-Object metric |
    Select-Object metric, limit, usage
$gpuRows | Format-Table -AutoSize | Out-Host

Write-Host "`nPreflight passed."

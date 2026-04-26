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

Write-Host "`n[1/6] gcloud installed"
& gcloud --version | Out-Host

Write-Host "`n[2/6] active account"
& gcloud auth list --filter=status:ACTIVE --format="value(account)" | Out-Host

Write-Host "`n[3/6] set project"
& gcloud config set project $ProjectId | Out-Host

Write-Host "`n[4/6] required services"
& gcloud services enable aiplatform.googleapis.com storage.googleapis.com --project $ProjectId | Out-Host

Write-Host "`n[5/6] bucket access"
& gcloud storage ls ("gs://{0}" -f $Bucket) | Out-Host

Write-Host "`n[6/6] quick Vertex region check"
& gcloud ai custom-jobs list --project $ProjectId --region $Region --limit 1 --format="table(name,state,createTime)" | Out-Host

Write-Host "`nPreflight passed."


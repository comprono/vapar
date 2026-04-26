param(
    [string]$ProjectId = $env:PROJECT_ID,
    [string]$Region = $env:REGION,
    [string]$Bucket = $env:GCS_BUCKET,
    [string]$Branch = $(if ($env:BRANCH) { $env:BRANCH } else { "codex/deep-crypto-colab-training" }),
    [string]$DisplayNamePrefix = $(if ($env:DISPLAY_NAME_PREFIX) { $env:DISPLAY_NAME_PREFIX } else { "deep-policy" }),
    [string]$MachineType = $(if ($env:MACHINE_TYPE) { $env:MACHINE_TYPE } else { "n1-standard-8" }),
    [string]$AcceleratorType = $(if ($env:ACCELERATOR_TYPE) { $env:ACCELERATOR_TYPE } else { "NVIDIA_TESLA_T4" }),
    [int]$AcceleratorCount = $(if ($env:ACCELERATOR_COUNT) { [int]$env:ACCELERATOR_COUNT } else { 1 }),
    [string]$ContainerImage = $(if ($env:CONTAINER_IMAGE) { $env:CONTAINER_IMAGE } else { "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest" }),
    [string]$ServiceAccount = $env:SERVICE_ACCOUNT,
    [string[]]$TrainArgs
)

$ErrorActionPreference = "Stop"

if (-not $ProjectId -or -not $Region -or -not $Bucket) {
    throw "Set PROJECT_ID, REGION, GCS_BUCKET (or pass -ProjectId, -Region, -Bucket)."
}

$ProjectId = $ProjectId.Trim()
$Region = $Region.Trim()
$Bucket = $Bucket.Trim()

if ($ProjectId -match "^\d+$") {
    throw "ProjectId must be the Google Cloud project ID, not the numeric project number. Use stellar-shard-376522."
}

if (-not $TrainArgs -or $TrainArgs.Count -eq 0) {
    $TrainArgs = @(
        "--years","5",
        "--window-size","128",
        "--train-lookback-days","1460",
        "--calibration-lookback-days","365",
        "--min-train-samples","2048",
        "--max-train-samples","30000",
        "--max-months","36",
        "--pretrain-epochs","25",
        "--epochs","35",
        "--batch-size","512",
        "--d-model","128",
        "--n-heads","8",
        "--n-layers","4",
        "--dropout","0.10",
        "--lr","0.0003",
        "--ranking-weight","1.0",
        "--initial-capital","10"
    )
}

$displayName = "{0}-{1}" -f $DisplayNamePrefix, (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$outputUri = "gs://{0}/vertex-runs/{1}" -f $Bucket, $displayName
$tmpConfig = [System.IO.Path]::GetTempFileName() + ".yaml"

foreach ($arg in $TrainArgs) {
    $s = [string]$arg
    if ($s -match "[\s'\""`$]") {
        throw "Unsupported TrainArgs token '$s'. Use simple flag/value tokens without spaces or quotes."
    }
}
$argsLiteral = ($TrainArgs | ForEach-Object { [string]$_ }) -join " "

$yaml = @"
workerPoolSpecs:
  - machineSpec:
      machineType: $MachineType
      acceleratorType: $AcceleratorType
      acceleratorCount: $AcceleratorCount
    replicaCount: 1
    containerSpec:
      imageUri: $ContainerImage
      command:
        - bash
      args:
        - -lc
        - |
          set -euo pipefail
          export PYTHONUNBUFFERED=1
          python -V
          pip install -q --upgrade pip
          pip install -q pandas numpy scipy scikit-learn yfinance python-binance google-cloud-storage
          mkdir -p /workspace && cd /workspace
          git clone --depth 1 --branch $Branch https://github.com/comprono/vapar.git repo
          cd repo
          python -u tests/run_deep_crypto_policy_walkforward.py $argsLiteral | tee /tmp/deep_policy_train.log
          python - <<'PY'
          from pathlib import Path
          from google.cloud import storage

          output_uri = "$outputUri"
          bucket_name, _, prefix = output_uri[5:].partition("/")
          prefix = prefix.strip("/")
          report_dirs = sorted(Path("data/reports").glob("deep_crypto_policy_*"), key=lambda p: p.stat().st_mtime)
          if not report_dirs:
              raise SystemExit("No deep_crypto_policy report directory found")
          latest = report_dirs[-1]
          client = storage.Client()
          bucket = client.bucket(bucket_name)
          artifact_prefix = f"{prefix}/artifacts/{latest.name}"
          for path in latest.rglob("*"):
              if path.is_file():
                  rel = path.relative_to(latest).as_posix()
                  bucket.blob(f"{artifact_prefix}/{rel}").upload_from_filename(str(path))
          log_path = Path("/tmp/deep_policy_train.log")
          if log_path.exists():
              bucket.blob(f"{prefix}/logs/deep_policy_train.log").upload_from_filename(str(log_path))
          print("Uploaded artifacts to:", f"gs://{bucket_name}/{artifact_prefix}")
          PY
baseOutputDirectory:
  outputUriPrefix: $outputUri/vertex-managed
"@

Set-Content -LiteralPath $tmpConfig -Value $yaml -Encoding UTF8

Write-Host "Submitting Vertex job: $displayName"
Write-Host "Project ID: $ProjectId"
Write-Host "Output prefix: $outputUri"

$cmd = @(
    "ai","custom-jobs","create",
    "--project",$ProjectId,
    "--region",$Region,
    "--display-name",$displayName,
    "--config",$tmpConfig
)

if ($ServiceAccount) {
    $cmd += @("--service-account",$ServiceAccount)
}

try {
    & gcloud @cmd
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud ai custom-jobs create failed with exit code $LASTEXITCODE."
    }
}
finally {
    Remove-Item -LiteralPath $tmpConfig -ErrorAction SilentlyContinue
}

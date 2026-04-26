@echo off
setlocal

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

set "PROJECT_ID=stellar-shard-376522"
set "REGION=us-central1"
set "GCS_BUCKET=tb1ag-vertex-artifacts-116514064160"
set "BRANCH=codex/deep-crypto-colab-training"
set "DISPLAY_NAME_PREFIX=deep-policy-debug"

set "GCLOUD_BIN=%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin"
if exist "%GCLOUD_BIN%\gcloud.cmd" set "PATH=%GCLOUD_BIN%;%PATH%"

echo ============================================================
echo Vertex Deep Policy DEBUG Train Submit
echo Project: %PROJECT_ID%
echo Region:  %REGION%
echo Bucket:  gs://%GCS_BUCKET%
echo Branch:  %BRANCH%
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\infra\gcp\submit_vertex_deep_policy_job.ps1" ^
  -TrainArgs ^
  --years 2 ^
  --symbols BTC-USD,ETH-USD,SOL-USD,BNB-USD ^
  --window-size 48 ^
  --train-lookback-days 540 ^
  --calibration-lookback-days 180 ^
  --min-train-samples 128 ^
  --max-train-samples 600 ^
  --max-months 1 ^
  --pretrain-epochs 1 ^
  --epochs 1 ^
  --batch-size 64 ^
  --d-model 32 ^
  --n-heads 4 ^
  --n-layers 1 ^
  --initial-capital 10

set "EXITCODE=%ERRORLEVEL%"
echo.
echo Finished. Exit code: %EXITCODE%
echo.
pause
exit /b %EXITCODE%


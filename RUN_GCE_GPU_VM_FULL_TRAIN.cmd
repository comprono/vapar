@echo off
setlocal

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

set "PROJECT_ID=stellar-shard-376522"
set "ZONE=us-central1-b"
set "INSTANCE_NAME=deep-policy-trainer-02"
set "GCS_BUCKET=tb1ag-vertex-artifacts-116514064160"
set "BRANCH=codex/deep-crypto-colab-training"
set "TRAIN_ARGS_LINE="

set "GCLOUD_BIN=%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin"
if exist "%GCLOUD_BIN%\gcloud.cmd" set "PATH=%GCLOUD_BIN%;%PATH%"

echo ============================================================
echo Run FULL Training on Persistent Compute Engine GPU VM
echo Project:  %PROJECT_ID%
echo Zone:     %ZONE%
echo Instance: %INSTANCE_NAME%
echo Bucket:   gs://%GCS_BUCKET%
echo Branch:   %BRANCH%
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\infra\gcp\run_gce_gpu_vm_training.ps1"

set "EXITCODE=%ERRORLEVEL%"
echo.
echo Finished. Exit code: %EXITCODE%
echo.
pause
exit /b %EXITCODE%

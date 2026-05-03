@echo off
setlocal

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

set "PROJECT_ID=stellar-shard-376522"
set "ZONE=us-central1-b"
set "INSTANCE_NAME=deep-policy-trainer-02"
set "MACHINE_TYPE=g2-standard-8"
set "GPU_TYPE=nvidia-l4"
set "GPU_COUNT=1"
set "BOOT_DISK_GB=200"
set "PROVISIONING_MODEL=STANDARD"

set "GCLOUD_BIN=%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin"
if exist "%GCLOUD_BIN%\gcloud.cmd" set "PATH=%GCLOUD_BIN%;%PATH%"

echo ============================================================
echo Create/Start Persistent Compute Engine L4 GPU VM
echo Project:  %PROJECT_ID%
echo Zone:     %ZONE%
echo Instance: %INSTANCE_NAME%
echo Machine:  %MACHINE_TYPE%
echo GPU:      %GPU_TYPE% x%GPU_COUNT%
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\infra\gcp\create_gce_gpu_vm.ps1"

set "EXITCODE=%ERRORLEVEL%"
echo.
echo Finished. Exit code: %EXITCODE%
echo.
pause
exit /b %EXITCODE%

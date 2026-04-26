@echo off
setlocal

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

set "PROJECT_ID=stellar-shard-376522"
set "REGION=us-central1"
set "GCS_BUCKET=tb1ag-vertex-artifacts-116514064160"

set "GCLOUD_BIN=%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin"
if exist "%GCLOUD_BIN%\gcloud.cmd" set "PATH=%GCLOUD_BIN%;%PATH%"

echo ============================================================
echo Vertex Preflight
echo Project: %PROJECT_ID%
echo Region:  %REGION%
echo Bucket:  gs://%GCS_BUCKET%
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\infra\gcp\vertex_preflight.ps1" ^
  -ProjectId "%PROJECT_ID%" ^
  -Region "%REGION%" ^
  -Bucket "%GCS_BUCKET%"

set "EXITCODE=%ERRORLEVEL%"
echo.
echo Finished. Exit code: %EXITCODE%
echo.
pause
exit /b %EXITCODE%


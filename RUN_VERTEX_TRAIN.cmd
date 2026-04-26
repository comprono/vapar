@echo off
setlocal

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

set "PROJECT_ID=stellar-shard-376522"
set "REGION=us-central1"
set "GCS_BUCKET=tb1ag-vertex-artifacts-116514064160"
set "BRANCH=codex/deep-crypto-colab-training"

set "GCLOUD_BIN=%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin"
if exist "%GCLOUD_BIN%\gcloud.cmd" set "PATH=%GCLOUD_BIN%;%PATH%"

set "PROJECT_ID=%PROJECT_ID%"
set "REGION=%REGION%"
set "GCS_BUCKET=%GCS_BUCKET%"
set "BRANCH=%BRANCH%"

echo ============================================================
echo Vertex Deep Policy Train Submit
echo Project: %PROJECT_ID%
echo Region:  %REGION%
echo Bucket:  gs://%GCS_BUCKET%
echo Branch:  %BRANCH%
echo ============================================================
echo.
if not "%~1"=="" (
  echo Custom training args: %*
  echo.
)

if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\infra\gcp\submit_vertex_deep_policy_job.ps1" ^
    -ProjectId "%PROJECT_ID%" ^
    -Region "%REGION%" ^
    -Bucket "%GCS_BUCKET%" ^
    -Branch "%BRANCH%"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\infra\gcp\submit_vertex_deep_policy_job.ps1" ^
    -ProjectId "%PROJECT_ID%" ^
    -Region "%REGION%" ^
    -Bucket "%GCS_BUCKET%" ^
    -Branch "%BRANCH%" ^
    -TrainArgs %*
)

set "EXITCODE=%ERRORLEVEL%"
echo.
echo Finished. Exit code: %EXITCODE%
echo.
pause
exit /b %EXITCODE%

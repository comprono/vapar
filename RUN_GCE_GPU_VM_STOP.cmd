@echo off
setlocal

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

set "PROJECT_ID=stellar-shard-376522"
set "ZONE=us-central1-a"
set "INSTANCE_NAME=deep-policy-trainer-01"

set "GCLOUD_BIN=%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin"
if exist "%GCLOUD_BIN%\gcloud.cmd" set "PATH=%GCLOUD_BIN%;%PATH%"

echo ============================================================
echo Stop Persistent Compute Engine GPU VM
echo Project:  %PROJECT_ID%
echo Zone:     %ZONE%
echo Instance: %INSTANCE_NAME%
echo ============================================================
echo.

gcloud compute instances stop "%INSTANCE_NAME%" --project "%PROJECT_ID%" --zone "%ZONE%"

set "EXITCODE=%ERRORLEVEL%"
echo.
echo Finished. Exit code: %EXITCODE%
echo.
pause
exit /b %EXITCODE%

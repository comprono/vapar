@echo off
title Frontend Dashboard (TB 1AG)
color 0B
echo ===================================================
echo    STARTING FRONTEND DASHBOARD (Next.js)
echo ===================================================
echo.
REM Use %~dp0 to automatically get the directory where this script is running
cd /d "%~dp0frontend"
npm run dev
pause

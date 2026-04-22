@echo off
title Backend Server (TB 1AG)
color 0A
echo ===================================================
echo    STARTING BACKEND SERVER (FastAPI)
echo ===================================================
echo.
REM Use %~dp0 to automatically get the directory where this script is running
cd /d "%~dp0"
python -m uvicorn backend.main:app --reload
pause

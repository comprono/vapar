@echo off
setlocal

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\show_10_dollar_progress.ps1"

echo.
pause

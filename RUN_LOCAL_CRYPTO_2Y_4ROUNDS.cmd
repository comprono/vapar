@echo off
setlocal

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

cls
echo ============================================================
echo  Local Crypto AutoLoop - 2 Years / 4 Rounds / $1000 Capital
echo ============================================================
echo.
echo Repo: %ROOT%
echo Started: %DATE% %TIME%
echo.

call "%ROOT%\run_local_crypto_autoloop.bat" --years 2 --iterations 4 --month-stride 1 --initial-capital 1000
set "EXITCODE=%ERRORLEVEL%"

echo.
echo ============================================================
echo Finished: %DATE% %TIME%
echo Exit code: %EXITCODE%
echo ============================================================
echo.
if not "%EXITCODE%"=="0" (
  echo The run failed. Copy the output above and send it back.
) else (
  echo The run completed. Check the data\reports folder for the newest report.
)
echo.
pause
exit /b %EXITCODE%

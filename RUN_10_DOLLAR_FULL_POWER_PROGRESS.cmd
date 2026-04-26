@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

for /f %%T in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss')"') do set "RUN_TAG=%%T"
for /f %%C in ('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum"') do set "CPU_THREADS=%%C"
if not defined CPU_THREADS set "CPU_THREADS=1"

set "LOG_DIR=%ROOT%\data\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\10usd_full_power_%RUN_TAG%.log"

set "PYTHONPATH=%ROOT%"
set "PYTHONUNBUFFERED=1"
set "CRYPTO_AUTORESEARCH_WORKERS=%CPU_THREADS%"
set "CRYPTO_FINAL_WALKFORWARD_WORKERS=%CPU_THREADS%"

rem Use one BLAS thread per worker so process-level parallelism can use the whole CPU cleanly.
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "OPENBLAS_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"

cls
echo ============================================================
echo  $10 Crypto Walk-Forward Training - Full CPU Progress Run
echo ============================================================
echo Repo: %ROOT%
echo Started UTC tag: %RUN_TAG%
echo Terminal log: %LOG_FILE%
echo.
echo CPU logical workers: %CPU_THREADS%
powershell -NoProfile -Command "Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors | Format-List"
echo GPU inventory from Windows:
powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion | Format-Table -AutoSize"
echo.
echo Note: this project currently trains with scikit-learn CPU models. The GPU is listed for audit,
echo but it will not be used unless the model stack is changed to a CUDA/DirectML trainer.
echo.
echo Progress you will see:
echo - each AutoResearch trial queued/completed
echo - each walk-forward month completed
echo - each loop round score, final $10 balance, best report, and verification paths
echo.
echo Reports saved under:
echo - data\reports\local_crypto_autoloop_*
echo - data\reports\crypto_autoresearch_*y_*.json
echo - data\reports\verification_*\portfolio_daily_verification.csv
echo - %LOG_FILE%
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\run_10_dollar_full_power_progress.ps1" -Root "%ROOT%" -LogFile "%LOG_FILE%" -CpuThreads "%CPU_THREADS%"
set "EXITCODE=%ERRORLEVEL%"

echo.
echo ============================================================
echo Finished. Exit code: %EXITCODE%
echo Full log: %LOG_FILE%
echo ============================================================
echo.
if "%EXITCODE%"=="0" (
  echo Latest $10 progress summary:
  powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\show_10_dollar_progress.ps1"
) else (
  echo The run failed. Open the log above and send the last error block back.
)
echo.
pause
exit /b %EXITCODE%

@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

for /f %%T in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss')"') do set "RUN_TAG=%%T"
for /f %%C in ('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum"') do set "CPU_THREADS=%%C"
if not defined CPU_THREADS set "CPU_THREADS=1"

set "LOG_DIR=%ROOT%\data\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\deep_crypto_policy_%RUN_TAG%.log"

set "PYTHONPATH=%ROOT%"
set "PYTHONUNBUFFERED=1"
set "OMP_NUM_THREADS=%CPU_THREADS%"
set "MKL_NUM_THREADS=%CPU_THREADS%"
set "OPENBLAS_NUM_THREADS=%CPU_THREADS%"
set "NUMEXPR_NUM_THREADS=%CPU_THREADS%"

cls
echo ============================================================
echo  Deep Crypto Transformer Policy - Progress Run
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
echo Note: local PyTorch will use CUDA only if this Python install has CUDA support.
echo This computer currently has CPU PyTorch, so this launcher is CPU training here.
echo.
echo Progress you will see:
echo - each walk-forward month
echo - calibration and production model training
echo - final model vs buy-hold return, risk, reports, and checkpoints
echo.
echo Reports saved under:
echo - data\reports\deep_crypto_policy_*
echo - %LOG_FILE%
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\run_deep_crypto_policy_progress.ps1" -Root "%ROOT%" -LogFile "%LOG_FILE%" -CpuThreads "%CPU_THREADS%"
set "EXITCODE=%ERRORLEVEL%"

echo.
echo ============================================================
echo Finished. Exit code: %EXITCODE%
echo Full log: %LOG_FILE%
echo ============================================================
echo.
if not "%EXITCODE%"=="0" (
  echo The run failed. Open the log above and send the last error block back.
)
echo.
pause
exit /b %EXITCODE%

@echo off
setlocal

set "ROOT=C:\Users\paras\Documents\antigravity files\TB 1AG"
cd /d "%ROOT%"

cls
echo ============================================================
echo  Local Crypto AutoLoop - 4 Hour Self-Improve Run
echo  5 Years / 20 Coins / $10 Total Portfolio
echo  Train/autoresearch: original 10 coins only
echo  Hidden verification: original 10 + 10 new coins
echo ============================================================
echo.
echo Repo: %ROOT%
echo Started: %DATE% %TIME%
set "CRYPTO_AUTORESEARCH_WORKERS=6"
set "CRYPTO_FINAL_WALKFORWARD_WORKERS=6"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "OPENBLAS_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
echo Trial CPU workers: %CRYPTO_AUTORESEARCH_WORKERS%
echo Final walk-forward workers: %CRYPTO_FINAL_WALKFORWARD_WORKERS%
echo.

call "%ROOT%\run_local_crypto_autoloop.bat" --years 5 --iterations 999 --time-budget-minutes 240 --month-stride 1 --initial-capital 10 --holdout-new-coins
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
  echo The run completed. Look for "Best final balance" above.
  echo The portfolio_daily_verification.csv path is printed above too.
)
echo.
pause
exit /b %EXITCODE%

@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%"
cd /d "%ROOT%"

echo [local-autoloop] Running local short-horizon crypto autoloop...
python "%ROOT%tests\run_crypto_local_autoloop.py" %*

if errorlevel 1 (
  echo [local-autoloop] Failed with exit code %errorlevel%
  exit /b %errorlevel%
)

echo [local-autoloop] Done.
exit /b 0

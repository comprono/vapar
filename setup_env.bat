@echo off
echo ===================================================
echo   Multi-Market Autonomous System - Bootstrap Script
echo ===================================================

echo.
echo [1/3] Checking Prerequisites...

where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not found. Please install Node.js ^(LTS^).
    pause
    exit /b 1
)

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found. Please install Python.
    pause
    exit /b 1
)

echo [OK] Node.js and Python found.

echo.
echo [2/3] Setting up Backend...
cd backend
if not exist "venv" (
    echo Creating Python Virtual Environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements.txt
cd ..

echo.
echo [3/3] Setting up Frontend (Next.js)...
if not exist "frontend\package.json" (
    echo Scaffolding Next.js App...
    REM remove directory if it exists and is empty to allow create-next-app
    if exist "frontend" rmdir frontend
    npx -y create-next-app@latest frontend --typescript --tailwind --eslint --no-src-dir --app --import-alias "@/*" --use-npm --yes
) else (
    echo Frontend already exists. Skipping creation.
)

echo.
echo ===================================================
echo   Setup Complete!
echo ===================================================
echo.
echo Please restart your agent session or tell the agent "Ready" to continue.
pause

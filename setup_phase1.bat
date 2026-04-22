@echo off
REM Automated Phase 1 Setup Script
REM This script automates what's possible without admin rights

echo ========================================
echo PHASE 1 SETUP AUTOMATION
echo ========================================

echo.
echo [1/3] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    exit /b 1
)

echo.
echo [2/3] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install psycopg2-binary python-binance numpy scipy pandas

if %errorlevel% neq 0 (
    echo WARNING: Some packages may have failed to install
)

echo.
echo [3/3] Checking Docker...
docker --version
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo DOCKER NOT INSTALLED
    echo ========================================
    echo.
    echo MANUAL STEPS REQUIRED:
    echo 1. Run the Docker Desktop installer (should be in Downloads)
    echo 2. Follow the installation wizard
    echo 3. Restart your computer
    echo 4. Run this script again
    echo.
    pause
    exit /b 1
)

echo.
echo [DOCKER FOUND] Starting database...
cd /d "%~dp0"
docker compose up -d

echo.
echo [VERIFICATION] Running tests...
python test_phase1.py

echo.
echo ========================================
echo SETUP COMPLETE!
echo ========================================
pause

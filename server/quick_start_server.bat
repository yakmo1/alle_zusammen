@echo off
REM Quick Start Script for Production Server
REM Windows Server 2012 - 24/7 Data Collection

echo ======================================================================
echo TRADING SYSTEM - PRODUCTION SERVER
echo Quick Start Script
echo ======================================================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator
) else (
    echo [WARNING] Not running as Administrator
    echo Some features may not work correctly
)

echo.
echo Checking prerequisites...
echo.

REM Check Python
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Python installed
    python --version
) else (
    echo [ERROR] Python not found
    echo Please install Python 3.13 first
    pause
    exit /b 1
)

echo.

REM Check PostgreSQL
psql --version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] PostgreSQL installed
    psql --version
) else (
    echo [WARNING] PostgreSQL command not found
    echo Make sure PostgreSQL is installed and running
)

echo.

REM Check MT5
if exist "C:\Program Files\MetaTrader 5\terminal64.exe" (
    echo [OK] MT5 Terminal found
) else (
    echo [WARNING] MT5 Terminal not found at default location
    echo Make sure MT5 is installed
)

echo.
echo ======================================================================
echo Starting Production Server...
echo ======================================================================
echo.

REM Change to script directory
cd /d %~dp0..

REM Start production server
python server\start_production_server.py

echo.
echo ======================================================================
echo Production Server stopped
echo ======================================================================
echo.

pause

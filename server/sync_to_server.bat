@echo off
REM Sync Workstation to Production Server
REM Uses Robocopy to mirror workspace to server

echo ======================================================================
echo SYNC WORKSPACE TO PRODUCTION SERVER
echo ======================================================================
echo.

REM Configuration
set WORKSTATION_PATH=C:\Projects\alle_zusammen\trading_system_unified
set SERVER_PATH=\\YOUR-SERVER-NAME\D$\Trading\trading_system_unified

echo Workstation: %WORKSTATION_PATH%
echo Server:      %SERVER_PATH%
echo.

REM Ask for confirmation
set /p CONFIRM="Do you want to sync to server? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Cancelled
    exit /b 0
)

echo.
echo ======================================================================
echo Syncing...
echo ======================================================================
echo.

REM Sync excluding logs and temporary files
robocopy "%WORKSTATION_PATH%" "%SERVER_PATH%" ^
    /MIR ^
    /Z ^
    /R:3 ^
    /W:5 ^
    /XD logs __pycache__ .git ^
    /XF *.pyc *.log *.tmp production_state.json ^
    /NFL /NDL /NP

echo.

if %errorLevel% LEQ 3 (
    echo ======================================================================
    echo [SUCCESS] Sync completed successfully
    echo ======================================================================
    echo.
    echo What was synced:
    echo   - All Python scripts
    echo   - Configuration files
    echo   - ML models
    echo   - Database schemas
    echo.
    echo What was excluded:
    echo   - Log files
    echo   - Temporary files
    echo   - Git history
    echo   - Python cache
    echo.
    echo ======================================================================
    echo NEXT STEPS:
    echo ======================================================================
    echo 1. Remote into server (mstsc /v:YOUR-SERVER-IP)
    echo 2. Open CMD and navigate to: D:\Trading\trading_system_unified
    echo 3. Run: server\quick_start_server.bat
    echo.
) else (
    echo [ERROR] Sync failed with error level: %errorLevel%
    echo.
    echo Common issues:
    echo   - Server not reachable
    echo   - Network path incorrect
    echo   - Insufficient permissions
    echo   - Server path does not exist
    echo.
    echo Please check:
    echo   1. Can you ping the server?
    echo   2. Is the server path correct?
    echo   3. Do you have write permissions?
    echo.
)

pause

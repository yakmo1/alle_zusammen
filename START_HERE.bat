@echo off
echo ====================================================================
echo TRADING SYSTEM UNIFIED - Setup und Start
echo ====================================================================
echo.

echo Schritt 1: Virtual Environment aktivieren
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo FEHLER: Virtual Environment nicht gefunden!
    echo Erstelle Virtual Environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installiere Dependencies...
    pip install -r requirements.txt
)

echo.
echo Schritt 2: System-Check
python scripts\quick_start.py
if errorlevel 1 (
    echo FEHLER beim System-Check!
    pause
    exit /b 1
)

echo.
echo Schritt 3: Datenbank initialisieren
echo Moechten Sie die Datenbank initialisieren? (J/N)
set /p init_db=
if /i "%init_db%"=="J" (
    python scripts\init_database.py --db local
)

echo.
echo ====================================================================
echo System bereit!
echo ====================================================================
echo.
echo Optionen:
echo [1] System starten (alle Komponenten)
echo [2] Nur Tick Collector testen (30 Sekunden)
echo [3] Nur Dashboard starten
echo [4] MT5 Connection testen
echo [5] Beenden
echo.
set /p choice=Ihre Wahl:

if "%choice%"=="1" (
    echo Starte System...
    python scripts\start_system.py
)
if "%choice%"=="2" (
    echo Starte Tick Collector Test...
    timeout /t 2
    python src\data\tick_collector.py
)
if "%choice%"=="3" (
    echo Starte Matrix Dashboard...
    echo Dashboard wird auf http://localhost:5000 verfuegbar sein
    python dashboards\matrix_dashboard\unified_master_dashboard.py
)
if "%choice%"=="4" (
    echo Teste MT5 Verbindung...
    python scripts\test_mt5_connection.py
)
if "%choice%"=="5" (
    exit
)

pause

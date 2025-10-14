# Server Deployment Guide - Windows Server 2012

## Übersicht

Dieses Dokument beschreibt die Einrichtung des Trading-Systems auf einem Windows Server 2012 für 24/7 Betrieb.

**Architektur**:
- **Workstation**: Entwicklung, Model Training, Testing
- **Server**: Produktion, 24/7 Datensammlung, Signal Generation

---

## Voraussetzungen

### Hardware
- ✅ Windows Server 2012 (oder neuer)
- ✅ Mindestens 4 GB RAM
- ✅ Mindestens 100 GB freier Festplattenspeicher
- ✅ Stabile Internetverbindung

### Software
- ✅ Python 3.13 (oder kompatibel)
- ✅ PostgreSQL 14+ (läuft bereits)
- ✅ MetaTrader 5 Terminal (installiert und eingeloggt)
- ✅ Git (optional, für Sync)

---

## Deployment-Schritte

### Schritt 1: Workspace auf Server synchronisieren

**Option A: Mit Git**
```bash
# Auf Workstation
cd C:\Projects\alle_zusammen\trading_system_unified
git add .
git commit -m "Deployment to production server"
git push

# Auf Server
cd D:\Trading  # oder anderer Pfad
git clone [REPO_URL] trading_system_unified
cd trading_system_unified
```

**Option B: Mit Robocopy (einfacher)**
```bash
# Von Workstation auf Server (über Netzwerk)
robocopy C:\Projects\alle_zusammen\trading_system_unified \\SERVER\D$\Trading\trading_system_unified /MIR /Z /R:3 /W:5 /NFL /NDL

# /MIR = Mirror (exakte Kopie)
# /Z = Restartable mode
# /R:3 = 3 Retries
# /W:5 = 5 Sekunden zwischen Retries
```

**Option C: Manuell**
- Kopiere den gesamten `trading_system_unified` Ordner auf den Server
- Z.B. nach `D:\Trading\trading_system_unified`

### Schritt 2: Python Dependencies installieren

```bash
# Auf Server
cd D:\Trading\trading_system_unified
pip install -r requirements.txt
```

### Schritt 3: Konfiguration anpassen

**Datei**: `config/system_config.json`

Überprüfen:
```json
{
  "database": {
    "postgresql": {
      "host": "localhost",
      "port": 5432,
      "database": "trading_db",
      "user": "postgres",
      "password": "dein_passwort"
    }
  },
  "mt5": {
    "login": 42811978,
    "password": "dein_mt5_passwort",
    "server": "MetaQuotes-Demo"
  }
}
```

### Schritt 4: PostgreSQL Verbindung testen

```bash
python -c "from src.data.database_manager import get_database; db = get_database('local'); print('Database OK!')"
```

### Schritt 5: MT5 Verbindung testen

```bash
python -c "import MetaTrader5 as mt5; mt5.initialize(); print('MT5 OK!' if mt5.account_info() else 'MT5 Failed'); mt5.shutdown()"
```

### Schritt 6: Production Server starten

```bash
# Auf Server
cd D:\Trading\trading_system_unified
python server\start_production_server.py
```

**Ausgabe sollte sein**:
```
======================================================================
PRODUCTION SERVER MANAGER
Windows Server 2012 - 24/7 Data Collection & Trading
======================================================================

Running on: YOUR-SERVER-NAME

======================================================================
PRODUCTION MODE - This will start 24/7 services
Press CTRL+C within 5 seconds to cancel
======================================================================

Starting production services...

Starting tick_collector_v2: Collects live tick data from MT5
✓ tick_collector_v2 started successfully (PID: 1234)

Starting bar_aggregator_v2: Aggregates ticks into OHLC bars
✓ bar_aggregator_v2 started successfully (PID: 1235)

Starting signal_generator: Generates trading signals from ML models
✓ signal_generator started successfully (PID: 1236)

======================================================================
ALL SERVICES STARTED SUCCESSFULLY
======================================================================

Running Services:
  • tick_collector_v2 (PID: 1234) - Collects live tick data from MT5
  • bar_aggregator_v2 (PID: 1235) - Aggregates ticks into OHLC bars
  • signal_generator (PID: 1236) - Generates trading signals from ML models

Server is now running 24/7. Press CTRL+C to stop all services.
```

---

## Als Windows Service einrichten (Optional)

Damit der Server automatisch beim Systemstart startet:

### Mit NSSM (Non-Sucking Service Manager)

1. **NSSM herunterladen**: https://nssm.cc/download
2. **NSSM installieren**:
   ```bash
   # Entpacken nach C:\Tools\nssm
   ```

3. **Service erstellen**:
   ```bash
   C:\Tools\nssm\nssm.exe install TradingSystemProduction
   ```

4. **In NSSM GUI konfigurieren**:
   - **Path**: `C:\Python313\python.exe`
   - **Startup directory**: `D:\Trading\trading_system_unified`
   - **Arguments**: `server\start_production_server.py`
   - **Service name**: `TradingSystemProduction`
   - **Display name**: `Trading System Production Server`
   - **Description**: `24/7 Data Collection and Signal Generation`

5. **Service starten**:
   ```bash
   net start TradingSystemProduction
   ```

6. **Automatischer Start beim Booten**:
   - Bereits aktiviert durch NSSM

---

## Monitoring

### Log-Dateien prüfen

**Server Logs**:
```bash
# Hauptlog
tail -f logs\server\production_server_20251014.log

# Service Logs
tail -f logs\scripts\tick_collector_v2_stdout.log
tail -f logs\scripts\bar_aggregator_v2_stdout.log
tail -f logs\scripts\signal_generator_stdout.log
```

### Service Status prüfen

```bash
# Produktion State File
type server\production_state.json
```

Beispiel:
```json
{
  "timestamp": "2025-10-14T15:30:00",
  "services": {
    "tick_collector_v2": {
      "pid": 1234,
      "started_at": "2025-10-14T15:00:00",
      "running": true,
      "description": "Collects live tick data from MT5"
    },
    "bar_aggregator_v2": {
      "pid": 1235,
      "started_at": "2025-10-14T15:00:05",
      "running": true,
      "description": "Aggregates ticks into OHLC bars"
    },
    "signal_generator": {
      "pid": 1236,
      "started_at": "2025-10-14T15:00:10",
      "running": true,
      "description": "Generates trading signals from ML models"
    }
  }
}
```

### Datenbank prüfen

```sql
-- Tick Count
SELECT
    'eurusd' as symbol,
    COUNT(*) as ticks
FROM ticks_eurusd_20251014
UNION ALL
SELECT
    'gbpusd' as symbol,
    COUNT(*) as ticks
FROM ticks_gbpusd_20251014;

-- Bar Count
SELECT
    symbol,
    timeframe,
    COUNT(*) as bars,
    MIN(timestamp) as first_bar,
    MAX(timestamp) as last_bar
FROM (
    SELECT 'EURUSD' as symbol, timeframe, timestamp FROM bars_eurusd
    UNION ALL
    SELECT 'GBPUSD' as symbol, timeframe, timestamp FROM bars_gbpusd
) combined
GROUP BY symbol, timeframe
ORDER BY symbol, timeframe;
```

---

## Workstation Setup (Entwicklung)

Auf der Workstation kannst du jetzt in Ruhe entwickeln, ohne die Datensammlung zu unterbrechen:

### Model Training (Workstation)

```bash
# Auf Workstation - Daten vom Server holen
# Option 1: Über Netzwerk direkt auf Server-DB zugreifen
# Option 2: DB Dump vom Server holen

# DB Dump erstellen (auf Server)
pg_dump -U postgres trading_db > backup_20251014.sql

# DB Dump auf Workstation importieren
psql -U postgres trading_db_dev < backup_20251014.sql

# Models trainieren
python scripts/train_model_simple.py --algorithm xgboost --timeframe 1m --horizon label_h5 --lookback 5
```

### Models auf Server deployen

```bash
# Auf Workstation
robocopy models \\SERVER\D$\Trading\trading_system_unified\models /MIR

# Oder nur neue Models
copy models\*.model \\SERVER\D$\Trading\trading_system_unified\models\
copy models\*.meta \\SERVER\D$\Trading\trading_system_unified\models\
```

### Signal Generator auf Server neu starten

```bash
# Auf Server - über Remote Desktop oder PowerShell Remoting
# Der Production Server wird automatisch den Signal Generator neu starten
# wenn neue Models erkannt werden

# Oder manuell:
# 1. CTRL+C im Production Server Fenster
# 2. python server\start_production_server.py
```

---

## Troubleshooting

### Problem: Services starten nicht

**Lösung 1**: Logs prüfen
```bash
type logs\scripts\tick_collector_v2_stderr.log
```

**Lösung 2**: MT5 Connection prüfen
```bash
python -c "import MetaTrader5 as mt5; print(mt5.initialize())"
```

**Lösung 3**: PostgreSQL Connection prüfen
```bash
psql -U postgres -d trading_db -c "SELECT 1"
```

### Problem: Datensammlung stoppt

**Symptom**: Keine neuen Ticks in DB

**Lösung**: Production Server neu starten
```bash
# Im Production Server Fenster
CTRL+C

# Warten bis alle Services stopped

# Neu starten
python server\start_production_server.py
```

### Problem: Zu viele Logs

**Lösung**: Log Rotation konfigurieren

Erstelle `server\cleanup_old_logs.py`:
```python
import os
from pathlib import Path
from datetime import datetime, timedelta

log_dir = Path(__file__).parent.parent / 'logs'
max_age_days = 30

for log_file in log_dir.rglob('*.log'):
    age = datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)
    if age > timedelta(days=max_age_days):
        log_file.unlink()
        print(f"Deleted old log: {log_file}")
```

Als Scheduled Task einrichten:
- Täglich um 3:00 Uhr
- `python D:\Trading\trading_system_unified\server\cleanup_old_logs.py`

### Problem: Server läuft nicht 24/7

**Lösung**: Windows Power Settings anpassen

```bash
# In Admin CMD
powercfg -change -standby-timeout-ac 0
powercfg -change -hibernate-timeout-ac 0
powercfg -change -disk-timeout-ac 0
powercfg -change -monitor-timeout-ac 0
```

---

## Backup Strategy

### Tägliches DB Backup (auf Server)

Erstelle `server\daily_backup.py`:
```python
import subprocess
from datetime import datetime
from pathlib import Path

backup_dir = Path("D:/Backups/trading_db")
backup_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = backup_dir / f"trading_db_{timestamp}.sql"

subprocess.run([
    "pg_dump",
    "-U", "postgres",
    "-d", "trading_db",
    "-f", str(backup_file)
])

print(f"Backup created: {backup_file}")

# Alte Backups löschen (älter als 7 Tage)
import os
from datetime import timedelta

for backup in backup_dir.glob("*.sql"):
    age = datetime.now() - datetime.fromtimestamp(backup.stat().st_mtime)
    if age > timedelta(days=7):
        backup.unlink()
        print(f"Deleted old backup: {backup}")
```

Als Scheduled Task:
- Täglich um 2:00 Uhr
- `python D:\Trading\trading_system_unified\server\daily_backup.py`

---

## Performance Optimization

### PostgreSQL Tuning (für Server)

In `postgresql.conf`:
```conf
# Memory
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
work_mem = 16MB

# Checkpoints
checkpoint_completion_target = 0.9
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB

# Connections
max_connections = 100

# Logging (reduzieren für Performance)
log_statement = 'none'
log_duration = off
```

Dann:
```bash
# PostgreSQL Service neu starten
net stop postgresql-x64-14
net start postgresql-x64-14
```

### Windows Performance

- ✅ Antivirus Ausnahmen für Trading-Ordner
- ✅ Deaktiviere Windows Updates während Trading-Zeiten
- ✅ Erhöhe Priorität für Python Prozesse

```bash
# Im Task Manager
# Rechtsklick auf python.exe -> Set Priority -> Above Normal
```

---

## Remote Access

### Remote Desktop

```bash
# Von Workstation
mstsc /v:SERVER_IP_ADDRESS
```

### PowerShell Remoting (fortgeschritten)

```powershell
# Auf Server (einmalig)
Enable-PSRemoting -Force

# Von Workstation
Enter-PSSession -ComputerName SERVER_NAME
cd D:\Trading\trading_system_unified
python server\start_production_server.py
```

---

## Checkliste für Go-Live

- [ ] Server Hardware OK (4GB+ RAM, 100GB+ Disk)
- [ ] Windows Server 2012 installiert
- [ ] Python 3.13 installiert
- [ ] PostgreSQL installiert und läuft
- [ ] MT5 Terminal installiert und eingeloggt
- [ ] Trading System Workspace synchronisiert
- [ ] Config angepasst (DB, MT5 Login)
- [ ] Dependencies installiert (`pip install -r requirements.txt`)
- [ ] DB Connection getestet
- [ ] MT5 Connection getestet
- [ ] Production Server gestartet
- [ ] Logs prüfen (keine Errors)
- [ ] Datensammlung läuft (Ticks in DB)
- [ ] Bar Aggregation läuft (Bars in DB)
- [ ] Optional: Als Windows Service eingerichtet
- [ ] Optional: Tägliches Backup eingerichtet
- [ ] Remote Access eingerichtet
- [ ] Power Settings angepasst (kein Standby)

---

## Kontakt & Support

Bei Problemen:
1. Logs prüfen (`logs/scripts/` und `logs/server/`)
2. DB Status prüfen (Tick/Bar Counts)
3. MT5 Connection prüfen
4. Production Server neu starten

**Wichtig**: Auf dem Server läuft NUR Datensammlung und Signal Generation.
Model Training und Development bleibt auf der Workstation!

---

**Version**: 1.0
**Datum**: 2025-10-14
**System**: Trading System Unified v3.0.0

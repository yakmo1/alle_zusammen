# Trading System Unified - Schritt-für-Schritt Anleitung

## Schnellstart (für Firefox-Test)

### Voraussetzungen prüfen

1. **PostgreSQL läuft?**
   ```
   Öffne: services.msc
   Suche: postgresql
   Status: "Wird ausgeführt"
   ```
   Falls nicht → Starten

2. **MT5 läuft?**
   ```
   Öffne: MetaTrader 5
   Prüfe: Verbindung aktiv (grüner Indikator unten rechts)
   ```

### System starten

**Option A: Mit START_HERE.bat (Empfohlen)**
```
1. Doppelklick auf: START_HERE.bat
2. Folge den Anweisungen
3. Wähle Option [3] für Dashboard
4. Firefox öffnet automatisch http://localhost:5000
```

**Option B: Manuell**
```
1. PowerShell öffnen als Administrator
2. cd C:\Projects\alle_zusammen\trading_system_unified
3. .\venv\Scripts\activate
4. python scripts\init_database.py --db local
5. python dashboards\matrix_dashboard\unified_master_dashboard.py
6. Firefox öffnen: http://localhost:5000
```

---

## Detaillierte Anleitung

### 1. Erstinstallation

#### 1.1 Virtual Environment erstellen
```powershell
cd C:\Projects\alle_zusammen\trading_system_unified
python -m venv venv
.\venv\Scripts\activate
```

#### 1.2 Dependencies installieren
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

**Wichtig:** Dies kann 5-10 Minuten dauern!

#### 1.3 PostgreSQL Datenbank erstellen

**In pgAdmin oder psql:**
```sql
CREATE DATABASE trading_db;
CREATE USER mt5user WITH PASSWORD '1234';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO mt5user;
```

**Oder in PowerShell:**
```powershell
psql -U postgres -c "CREATE DATABASE trading_db;"
psql -U postgres -c "CREATE USER mt5user WITH PASSWORD '1234';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE trading_db TO mt5user;"
```

#### 1.4 Datenbank initialisieren
```powershell
python scripts\init_database.py --db local
```

**Erwartete Ausgabe:**
```
============================================================
Trading System - Database Initialization
============================================================

### Initializing LOCAL Database ###
Connected to local database
Creating table: bars_5s
✓ Table bars_5s created/verified
Creating table: bars_1m
✓ Table bars_1m created/verified
...
✓ Database initialization complete (local)
```

---

### 2. System testen

#### 2.1 Config-Test
```powershell
python scripts\quick_start.py
```

**Alle Tests sollten "OK" zeigen!**

#### 2.2 MT5 Connection Test
```powershell
python scripts\test_mt5_connection.py
```

**Erwartete Ausgabe:**
```
============================================================
MetaTrader 5 Connection Test
============================================================

### MT5 Configuration ###
Server: admiralsgroup-demo
Login: 42771818

✓ MT5 initialized
✓ Login successful

### Account Information ###
Name: ...
Balance: 10000.00 EUR
...

✓ ALL TESTS PASSED
```

**Falls Fehler:**
- Prüfe ob MT5 läuft
- Prüfe ob in MT5 eingeloggt
- Prüfe MT5_PATH in .env

#### 2.3 Data Pipeline Test (Optional)

**Tick Collector (30 Sekunden):**
```powershell
python src\data\tick_collector.py
```

**Erwartete Ausgabe:**
```
=== Tick Collector Test ===

✓ MT5 connected
✓ Tick collector started for symbols: EURUSD
Collecting ticks for 30 seconds...
✓ Tick collector stopped

Statistics:
  ticks_collected: 250
  ticks_written: 250
  ...
```

---

### 3. Dashboard starten und testen

#### 3.1 Matrix Dashboard starten
```powershell
python dashboards\matrix_dashboard\unified_master_dashboard.py
```

**Erwartete Ausgabe:**
```
 * Running on http://0.0.0.0:5000
 * Running on http://127.0.0.1:5000
```

#### 3.2 Firefox öffnen

1. **Firefox starten**
2. **URL eingeben:** `http://localhost:5000`
3. **Erwartetes Ergebnis:**
   - Matrix-Style Dashboard
   - Real-time Updates
   - Trading-Übersicht
   - System-Monitoring

#### 3.3 Fehlersuche im Dashboard

**Falls Dashboard nicht lädt:**

1. **Prüfe Console (F12 in Firefox):**
   - Gehe zu "Konsole"
   - Suche nach roten Fehlermeldungen
   - Screenshot machen!

2. **Prüfe Netzwerk (F12 → Netzwerk):**
   - Werden Requests abgeschickt?
   - Gibt es 404 oder 500 Fehler?
   - Screenshot machen!

3. **Prüfe PowerShell/CMD wo Dashboard läuft:**
   - Gibt es Python-Fehler?
   - Gibt es Datenbankfehler?

**Häufige Fehler:**

- **"connection refused"** → Dashboard läuft nicht, neu starten
- **"database error"** → PostgreSQL läuft nicht oder DB nicht initialisiert
- **"no data"** → Tick Collector wurde noch nicht gestartet, keine Daten vorhanden
- **"MT5 error"** → MT5 nicht verbunden

---

### 4. Vollständiges System starten

#### 4.1 Alle Komponenten starten
```powershell
python scripts\start_system.py
```

Dies startet:
- ✓ Tick Collector (sammelt Live-Daten von MT5)
- ✓ Bar Builder (erstellt OHLC Bars)
- ✓ Feature Calculator (berechnet Indicators)
- ✓ Matrix Dashboard (http://localhost:5000)

**Zum Stoppen:** `Strg + C`

#### 4.2 Komponenten überwachen

**In separaten PowerShell-Fenstern:**

**Fenster 1 - Logs:**
```powershell
Get-Content logs\trading_system.log -Wait
```

**Fenster 2 - Dashboard:**
```
Firefox: http://localhost:5000
```

**Fenster 3 - Database Monitor:**
```powershell
# Anzahl Ticks
python -c "from src.data.database_manager import get_database; db = get_database(); print(db.get_table_row_count('ticks_20251012'))"

# Anzahl Bars
python -c "from src.data.database_manager import get_database; db = get_database(); print(db.get_table_row_count('bars_1m'))"
```

---

### 5. Troubleshooting-Checkliste

#### Problem: "Database connection failed"

**Lösung:**
```powershell
# 1. Prüfe ob PostgreSQL läuft
Get-Service -Name postgresql*

# 2. Starte PostgreSQL falls nötig
Start-Service -Name postgresql-x64-13  # (oder deine Version)

# 3. Teste Connection
psql -h localhost -U mt5user -d trading_db
# Passwort: 1234

# 4. Prüfe Firewall
# Windows Firewall → Port 5432 erlauben
```

#### Problem: "MT5 initialization failed"

**Lösung:**
```
1. MT5 öffnen
2. Datei → Mit Handelskonto anmelden
3. Server: admiralsgroup-demo
4. Login: 42771818
5. Passwort: i6K44O&6A6j%Ec
6. Anmelden
7. Script neu starten
```

#### Problem: "No module named 'xxx'"

**Lösung:**
```powershell
# Virtual Environment aktivieren
.\venv\Scripts\activate

# Dependencies neu installieren
pip install -r requirements.txt

# Spezifisches Package installieren
pip install xxx
```

#### Problem: "Permission denied"

**Lösung:**
```
1. PowerShell als Administrator öffnen
2. Oder: Execution Policy ändern
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 6. Logs und Debugging

#### 6.1 Log-Locations
```
logs\
├── trading_system.log          # Haupt-Log
├── trading_system.log.1        # Backup 1
├── trading_system.log.2        # Backup 2
...
```

#### 6.2 Log Level ändern

**In .env:**
```
LOG_LEVEL=DEBUG  # Sehr detailliert
LOG_LEVEL=INFO   # Normal (Standard)
LOG_LEVEL=WARNING  # Nur Warnungen
LOG_LEVEL=ERROR  # Nur Fehler
```

#### 6.3 Logs live anschauen
```powershell
# PowerShell
Get-Content logs\trading_system.log -Wait -Tail 50

# CMD
powershell Get-Content logs\trading_system.log -Wait -Tail 50
```

---

### 7. Performance-Optimierung

#### 7.1 Database Performance prüfen
```sql
-- In pgAdmin oder psql
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
       n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### 7.2 Vacuum Database (regelmäßig!)
```powershell
python -c "from src.data.database_manager import get_database; db = get_database(); [db.vacuum_table(t) for t in db.list_tables()]"
```

---

### 8. Nächste Schritte nach erfolgreichem Test

1. **ML System integrieren**
   - Models aus autotrading_10 übernehmen
   - Training Pipeline einrichten

2. **Trading Engine aktivieren**
   - Risk Management konfigurieren
   - Auto-Trading NOCH NICHT aktivieren!

3. **Paper Trading (Demo-Account)**
   - 1-2 Wochen testen
   - Performance monitoren

4. **Live Trading vorbereiten**
   - Erst nach erfolgreichen Paper Trading!
   - Mit kleinem Kapital starten

---

## Support

**Bei Problemen:**

1. **Logs prüfen:** `logs\trading_system.log`
2. **Quick Start ausführen:** `python scripts\quick_start.py`
3. **System-Status:** `python scripts\system_health_check.py` (falls vorhanden)

**Screenshots erstellen von:**
- Firefox Developer Tools (F12) → Console
- Firefox Developer Tools (F12) → Network
- PowerShell Output
- Fehlermeldungen

---

**Version:** 1.0.0-alpha
**Datum:** 2025-10-12

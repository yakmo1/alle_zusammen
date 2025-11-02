# Server Setup - Zusammenfassung

**Datum**: 2025-10-14
**Status**: READY FOR DEPLOYMENT

---

## Was wurde erstellt?

Du hast jetzt ein vollständiges **Production Server Setup** für deinen Windows Server 2012!

### Neue Dateien im `server/` Verzeichnis:

1. **start_production_server.py** (221 Zeilen)
   - Hauptskript für 24/7 Betrieb
   - Startet alle Services automatisch
   - Überwacht Services und startet sie bei Fehler neu
   - Schreibt Production State in JSON

2. **config_production.json**
   - Production Konfiguration
   - Service Einstellungen
   - Risk Management Parameter
   - Paper Trading Mode aktiviert

3. **SERVER_DEPLOYMENT_GUIDE.md** (500+ Zeilen)
   - Vollständige Deployment-Dokumentation
   - Schritt-für-Schritt Anleitung
   - Troubleshooting
   - Performance Tuning
   - Backup Strategy

4. **quick_start_server.bat**
   - Windows Batch für schnellen Start
   - Prüft Prerequisites (Python, PostgreSQL, MT5)
   - Startet Production Server

5. **sync_to_server.bat**
   - Synchronisiert Workspace von Workstation zu Server
   - Verwendet Robocopy (Mirror Mode)
   - Excludiert Logs und Temp-Dateien

6. **README.md**
   - Quick-Start Guide
   - Übersicht aller Services
   - Monitoring Commands
   - Troubleshooting Tips

---

## Architektur

```
┌─────────────────────────────────────────────────────────┐
│                  WORKSTATION                             │
│  (Development - Du arbeitest hier)                      │
├─────────────────────────────────────────────────────────┤
│  • Model Training                                       │
│  • Feature Engineering                                  │
│  • Testing & Debugging                                  │
│  • Dashboard Development                                │
│  • Code Änderungen                                      │
└─────────────────────────────────────────────────────────┘
                      │
                      │ Sync (Robocopy/Git)
                      ▼
┌─────────────────────────────────────────────────────────┐
│           WINDOWS SERVER 2012                            │
│  (Production - Läuft 24/7)                              │
├─────────────────────────────────────────────────────────┤
│  • Tick Collector V2  ───► 1M+ Ticks gesammelt         │
│  • Bar Aggregator V2  ───► OHLC Bars (5 Timeframes)    │
│  • Signal Generator   ───► Trading Signals (Paper)      │
│  • PostgreSQL DB      ───► Alle Daten persistent        │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start Guide

### Schritt 1: Workspace auf Server kopieren

**Auf deiner Workstation**:

1. Öffne `server\sync_to_server.bat` in einem Editor
2. Ändere die Zeile:
   ```batch
   set SERVER_PATH=\\YOUR-SERVER-NAME\D$\Trading\trading_system_unified
   ```
   zu deinem Server-Pfad, z.B.:
   ```batch
   set SERVER_PATH=\\MY-SERVER\D$\Trading\trading_system_unified
   ```

3. Führe aus:
   ```bash
   server\sync_to_server.bat
   ```

**Alternativ** (manuell):
```bash
# Ganzen Ordner auf USB-Stick kopieren und auf Server übertragen
# Oder über Netzwerk-Share
```

### Schritt 2: Auf Server einloggen

```bash
# Remote Desktop
mstsc /v:DEINE-SERVER-IP
```

### Schritt 3: Production Server starten

**Im Server CMD**:
```bash
cd D:\Trading\trading_system_unified
server\quick_start_server.bat
```

**Ausgabe**:
```
======================================================================
TRADING SYSTEM - PRODUCTION SERVER
Quick Start Script
======================================================================

[OK] Running as Administrator
[OK] Python installed
Python 3.13.0
[OK] PostgreSQL installed
[OK] MT5 Terminal found

======================================================================
Starting Production Server...
======================================================================

Starting tick_collector_v2: Collects live tick data from MT5
✓ tick_collector_v2 started successfully (PID: 1234)

Starting bar_aggregator_v2: Aggregates ticks into OHLC bars
✓ bar_aggregator_v2 started successfully (PID: 1235)

Starting signal_generator: Generates trading signals from ML models
✓ signal_generator started successfully (PID: 1236)

======================================================================
ALL SERVICES STARTED SUCCESSFULLY
======================================================================

Server is now running 24/7. Press CTRL+C to stop all services.
```

**Das war's!** Der Server sammelt jetzt 24/7 Daten.

---

## Was läuft jetzt auf dem Server?

### Service 1: Tick Collector V2
- Sammelt Live-Ticks von MT5
- Alle 2 Sekunden ~50 Ticks pro Symbol
- 5 Symbole: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD
- Schreibt in PostgreSQL (`ticks_eurusd_20251014` Tabellen)

### Service 2: Bar Aggregator V2
- Liest Ticks aus DB
- Erstellt OHLC Bars
- 5 Timeframes: 1m, 5m, 15m, 1h, 4h
- Schreibt in `bars_eurusd`, `bars_gbpusd` usw.

### Service 3: Signal Generator
- Lädt ML Models (XGBoost, LightGBM)
- Holt letzte 6 Bars pro Symbol
- Berechnet Features
- Macht Predictions
- Generiert BUY/SELL Signale
- **Paper Trading Mode** - keine echten Orders!
- Speichert Signale in `signals` Tabelle

---

## Monitoring

### Auf dem Server prüfen:

```bash
# Service Status
type server\production_state.json

# Logs
type logs\scripts\tick_collector_v2_stdout.log
type logs\scripts\bar_aggregator_v2_stdout.log
type logs\scripts\signal_generator_stdout.log

# Datenbank
psql -U postgres -d trading_db -c "SELECT COUNT(*) FROM ticks_eurusd_20251014"
psql -U postgres -d trading_db -c "SELECT COUNT(*) FROM bars_eurusd WHERE timeframe='1m'"
```

### Von der Workstation aus prüfen:

```bash
# Über Netzwerk (wenn Server-DB öffentlich)
psql -h SERVER-IP -U postgres -d trading_db -c "SELECT COUNT(*) FROM ticks_eurusd_20251014"

# Oder Dashboard auf Server aufrufen (wenn Dashboard läuft)
# http://SERVER-IP:8000
```

---

## Development Workflow

### 1. Auf Workstation entwickeln

```bash
# Auf Workstation
cd C:\Projects\alle_zusammen\trading_system_unified

# Code ändern, testen...
# Models trainieren
python scripts\train_model_simple.py --algorithm xgboost --timeframe 1m --horizon label_h5 --lookback 5

# Neue Models sind jetzt in models/
```

### 2. Models zu Server deployen

```bash
# Option 1: Kompletter Sync
server\sync_to_server.bat

# Option 2: Nur Models
copy models\*.model \\SERVER\D$\Trading\trading_system_unified\models\
copy models\*.meta \\SERVER\D$\Trading\trading_system_unified\models\
```

### 3. Signal Generator neu starten (auf Server)

```bash
# Im Production Server Fenster auf dem Server
CTRL+C  # Stoppt alle Services

# Neu starten
server\quick_start_server.bat
```

Der Signal Generator lädt dann automatisch die neuen Models!

---

## Wichtige Hinweise

### ✅ Was du SOLLST auf dem Server machen:
- Datensammlung laufen lassen (24/7)
- Logs prüfen
- Services überwachen
- Signale prüfen (später in Phase 4)

### ❌ Was du NICHT auf dem Server machen sollst:
- Model Training (zu langsam, mach das auf Workstation)
- Dashboard Development (mach das auf Workstation)
- Debugging (mach das auf Workstation)
- Code-Änderungen (mach das auf Workstation, dann sync)

### ⚠️ Safety Features aktiv:
- Paper Trading Mode (keine echten Orders)
- Max 10 Signals pro Stunde
- Max $500 Daily Loss Limit
- Max 3 Positionen gleichzeitig
- Max 10% Drawdown Limit
- Spread Filter (max 2 pips)

---

## Timeline bis Live Trading

### Heute (Tag 1)
- ✅ Server aufgesetzt
- ✅ Datensammlung gestartet
- ⏳ 24 Stunden laufen lassen

### Morgen (Tag 2)
- Daten prüfen (sollten ~1440 Bars pro Symbol sein)
- Models neu trainieren (mit 1000+ Samples)
- Signal Generator testen mit neuen Models

### Woche 1-4
- Paper Trading laufen lassen
- Signal Quality tracken
- Performance Metriken sammeln
- Dashboard für Signal Analytics erstellen

### Woche 5
- Paper Trading Results evaluieren
- Wenn positiv: Phase 4 (Auto Trader) implementieren
- Live Trading vorbereiten

### Woche 6-8
- Live Trading mit kleinem Kapital starten
- Eng monitoren
- Optimieren

### Monat 3-6
- Skalieren (mehr Kapital)
- Mehr Symbole hinzufügen
- Fortgeschrittene Strategien

---

## Troubleshooting

### Problem: Services starten nicht

**Lösung**:
```bash
# Logs prüfen
type logs\scripts\tick_collector_v2_stderr.log

# MT5 prüfen
python -c "import MetaTrader5 as mt5; print(mt5.initialize())"

# PostgreSQL prüfen
psql -U postgres -d trading_db -c "SELECT 1"
```

### Problem: Keine Daten in DB

**Lösung**:
```bash
# Ist Tick Collector am laufen?
tasklist | findstr python

# Ist MT5 eingeloggt?
# MT5 Terminal öffnen und prüfen

# DB Connection OK?
psql -U postgres -d trading_db
```

### Problem: Server zu langsam

**Lösung**:
- PostgreSQL tuning (siehe SERVER_DEPLOYMENT_GUIDE.md)
- Python Prozess Priorität erhöhen (Task Manager)
- Antivirus Ausnahme für Trading-Ordner

---

## Nächste Schritte

### Jetzt sofort:
1. ✅ Workspace auf Server syncen
2. ✅ Production Server starten
3. ✅ 24 Stunden laufen lassen

### Morgen:
4. Daten prüfen (sollten 1440+ Bars sein)
5. Models neu trainieren mit mehr Daten
6. Signal Generator mit neuen Models testen

### Nächste Woche:
7. Phase 4 implementieren (Auto Trader)
8. Paper Trading für 4 Wochen
9. Signal Quality Dashboard

---

## Support Files

📖 **Vollständige Dokumentation**: [server/SERVER_DEPLOYMENT_GUIDE.md](server/SERVER_DEPLOYMENT_GUIDE.md)

🔧 **Configuration**: [server/config_production.json](server/config_production.json)

🚀 **Quick Start**: [server/README.md](server/README.md)

📊 **System Status**: `type server\production_state.json`

---

## Zusammenfassung

Du hast jetzt:
- ✅ Production Server Script (24/7 Betrieb)
- ✅ Automatisches Service Management
- ✅ Monitoring & Logging
- ✅ Sync-Skripte (Workstation ↔ Server)
- ✅ Vollständige Dokumentation
- ✅ Safety Features (Paper Trading, Limits)

**Der Server kann jetzt 24/7 Daten sammeln, während du auf der Workstation in Ruhe entwickelst!**

**Nächster Milestone**: Morgen nach 24h Datensammlung → Models neu trainieren → Phase 4 (Auto Trader)

---

**Version**: 1.0
**Datum**: 2025-10-14
**System**: Trading System Unified v3.0.0
**Status**: READY FOR PRODUCTION 🚀

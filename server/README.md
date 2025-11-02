# Production Server Setup

Dieses Verzeichnis enthält alle Dateien für den Betrieb des Trading-Systems auf einem Windows Server 2012 für 24/7 Datensammlung.

## Quick Start (für Server)

### 1. Workspace auf Server kopieren

**Von Workstation aus**:
```bash
# Server-Pfad anpassen in sync_to_server.bat
# Dann ausführen:
server\sync_to_server.bat
```

### 2. Auf Server einloggen

```bash
# Remote Desktop
mstsc /v:YOUR-SERVER-IP
```

### 3. Production Server starten

```bash
# Im Server CMD
cd D:\Trading\trading_system_unified
server\quick_start_server.bat
```

**Fertig!** Der Server sammelt jetzt 24/7 Daten.

---

## Dateien in diesem Verzeichnis

| Datei | Beschreibung |
|-------|-------------|
| `start_production_server.py` | Hauptskript - Startet alle Services |
| `config_production.json` | Production Konfiguration |
| `quick_start_server.bat` | Windows Batch für schnellen Start |
| `sync_to_server.bat` | Sync von Workstation zu Server |
| `SERVER_DEPLOYMENT_GUIDE.md` | Vollständige Dokumentation (80+ Seiten) |
| `production_state.json` | Status aller laufenden Services |

---

## Was läuft auf dem Server?

```
┌─────────────────────────────────────────┐
│     PRODUCTION SERVER (24/7)            │
├─────────────────────────────────────────┤
│                                         │
│  ✓ Tick Collector V2                   │
│    → Sammelt Live-Ticks von MT5        │
│    → Schreibt in PostgreSQL            │
│                                         │
│  ✓ Bar Aggregator V2                   │
│    → Erstellt OHLC Bars aus Ticks      │
│    → 5 Timeframes (1m, 5m, 15m, 1h, 4h)│
│                                         │
│  ✓ Signal Generator                    │
│    → Lädt ML Models                    │
│    → Generiert Trading Signals         │
│    → Paper Trading Mode                │
│                                         │
│  ✓ PostgreSQL Database                 │
│    → Speichert alle Daten              │
│                                         │
└─────────────────────────────────────────┘
```

---

## Was läuft auf der Workstation?

```
┌─────────────────────────────────────────┐
│     WORKSTATION (Development)           │
├─────────────────────────────────────────┤
│                                         │
│  ✓ Model Training                      │
│    → Traininiert ML Models             │
│    → Evaluiert Performance             │
│                                         │
│  ✓ Testing & Debugging                 │
│    → Testet neue Features              │
│    → Debuggt Probleme                  │
│                                         │
│  ✓ Dashboard Development               │
│    → Entwickelt neue Features          │
│    → Visualisierungen                  │
│                                         │
│  ✓ Model Deployment                    │
│    → Sync neue Models zu Server        │
│                                         │
└─────────────────────────────────────────┘
```

---

## Monitoring

### Logs prüfen (auf Server)

```bash
# Alle Services
type logs\server\production_server_20251014.log

# Einzelne Services
type logs\scripts\tick_collector_v2_stdout.log
type logs\scripts\bar_aggregator_v2_stdout.log
type logs\scripts\signal_generator_stdout.log
```

### Status prüfen

```bash
# Service Status
type server\production_state.json

# Datenbank Status
psql -U postgres -d trading_db -c "SELECT COUNT(*) FROM ticks_eurusd_20251014"
```

---

## Deployment Workflow

```
┌──────────────┐         ┌──────────────┐
│  WORKSTATION │─────────│    SERVER    │
│              │  Sync   │   (24/7)     │
└──────────────┘         └──────────────┘
      │                         │
      │                         │
      ▼                         ▼
┌──────────────┐         ┌──────────────┐
│ Development  │         │ Production   │
│ - Training   │         │ - Data Coll. │
│ - Testing    │         │ - Signals    │
│ - Coding     │         │ - Trading    │
└──────────────┘         └──────────────┘
```

### Schritt 1: Entwickeln auf Workstation
```bash
# Auf Workstation
cd C:\Projects\alle_zusammen\trading_system_unified

# Code ändern, Models trainieren, testen...
python scripts\train_model_simple.py --algorithm xgboost
```

### Schritt 2: Sync zu Server
```bash
# Auf Workstation
server\sync_to_server.bat
```

### Schritt 3: Server neu starten (falls nötig)
```bash
# Auf Server (Remote Desktop)
# Im Production Server Fenster: CTRL+C
# Dann neu starten:
server\quick_start_server.bat
```

---

## Troubleshooting

### Problem: Services starten nicht

**Logs prüfen**:
```bash
type logs\scripts\*_stderr.log
```

**MT5 Connection testen**:
```bash
python -c "import MetaTrader5 as mt5; print(mt5.initialize())"
```

### Problem: Keine Daten in DB

**Tick Collector läuft?**
```bash
tasklist | findstr python
```

**DB Connection OK?**
```bash
psql -U postgres -d trading_db -c "SELECT 1"
```

### Problem: Zu viele Logs

```bash
# Alte Logs löschen (älter als 30 Tage)
forfiles /p logs /s /m *.log /d -30 /c "cmd /c del @path"
```

---

## Als Windows Service einrichten

Siehe [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md) Abschnitt "Als Windows Service einrichten"

Kurz:
1. NSSM herunterladen: https://nssm.cc/download
2. Service erstellen: `nssm install TradingSystemProduction`
3. Path: `python.exe`
4. Arguments: `server\start_production_server.py`
5. Service starten: `net start TradingSystemProduction`

---

## Backup

**Tägliches DB Backup** (empfohlen):

```bash
# Als Scheduled Task einrichten
pg_dump -U postgres trading_db > D:\Backups\trading_db_%date%.sql
```

---

## Support & Dokumentation

📖 **Vollständige Dokumentation**: [SERVER_DEPLOYMENT_GUIDE.md](SERVER_DEPLOYMENT_GUIDE.md)

🔧 **Configuration**: [config_production.json](config_production.json)

📊 **System Health**: `type server\production_state.json`

---

## Wichtige Hinweise

⚠️ **Auf dem Server läuft NUR**:
- Datensammlung (Tick Collector, Bar Aggregator)
- Signal Generation
- PostgreSQL Database

⚠️ **Model Training bleibt auf Workstation**:
- Nicht auf Server trainieren (Performance)
- Models nach Training zu Server syncen

⚠️ **Paper Trading Mode**:
- Signal Generator läuft im Paper Trading Mode
- Keine echten Orders werden platziert
- Erst nach 4 Wochen Validierung auf Live umstellen

---

**Version**: 1.0
**Datum**: 2025-10-14
**System**: Trading System Unified v3.0.0

# Trading System Unified - Deployment Guide

Vollständiger Leitfaden für Setup und Deployment des Trading Systems.

## Inhaltsverzeichnis

1. [Voraussetzungen](#voraussetzungen)
2. [Installation](#installation)
3. [Konfiguration](#konfiguration)
4. [Datenbank Setup](#datenbank-setup)
5. [MT5 Setup](#mt5-setup)
6. [System Start](#system-start)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Production Deployment](#production-deployment)

---

## Voraussetzungen

### Software
- **Python 3.9+** (empfohlen: 3.11)
- **PostgreSQL 13+** (lokal und/oder remote)
- **MetaTrader 5** Terminal (installiert und konfiguriert)
- **Git** (für Version Control)

### Hardware (Minimum)
- **CPU:** 4 Cores
- **RAM:** 8 GB
- **Storage:** 50 GB SSD
- **Network:** Stabile Internetverbindung

### Empfohlen für Production
- **CPU:** 8+ Cores
- **RAM:** 16+ GB
- **Storage:** 100+ GB NVMe SSD
- **Network:** Dedicated Server / VPS

---

## Installation

### 1. Repository Setup

```bash
cd C:\Projects\alle_zusammen\trading_system_unified
```

### 2. Virtual Environment

```bash
# Erstellen
python -m venv venv

# Aktivieren (Windows)
.\venv\Scripts\activate

# Aktivieren (Linux/Mac)
source venv/bin/activate
```

### 3. Dependencies installieren

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Installation verifizieren

```bash
python -c "import MetaTrader5; import psycopg2; import xgboost; print('✓ All dependencies installed')"
```

---

## Konfiguration

### 1. Environment Variables (.env)

Kopiere `.env.example` nach `.env` (oder nutze vorhandene `.env`):

```bash
# MetaTrader 5
MT5_LOGIN=42771818
MT5_PASSWORD=your_password_here
MT5_SERVER=admiralsgroup-demo
MT5_PATH=C:\Program Files\Admirals Group MT5 Terminal\terminal64.exe

# Database - Local
DB_HOST_LOCAL=localhost
DB_PORT_LOCAL=5432
DB_NAME_LOCAL=trading_db
DB_USER_LOCAL=mt5user
DB_PASSWORD_LOCAL=1234

# Database - Remote
DB_HOST_REMOTE=212.132.105.198
DB_PORT_REMOTE=5432
DB_NAME_REMOTE=postgres
DB_USER_REMOTE=mt5user
DB_PASSWORD_REMOTE=1234

# Active Database
DB_ACTIVE=local

# Trading
ENABLE_AUTO_TRADING=false  # Auf true setzen für Live Trading!
```

**WICHTIG:**
- Setze `ENABLE_AUTO_TRADING=false` für Testing/Development
- Setze `ENABLE_AUTO_TRADING=true` nur für Production

### 2. Config.json anpassen

Prüfe/bearbeite `config/config.json`:

```json
{
  "database": {
    "active": "local"  // oder "remote"
  },
  "mt5": {
    "login": 42771818,
    "server": "admiralsgroup-demo"
  },
  "trading": {
    "enable_auto_trading": false,  // Auf true für Live Trading!
    "risk_per_trade": 0.02,        // 2% Risiko pro Trade
    "max_daily_loss": 0.05         // 5% Max Daily Loss
  }
}
```

---

## Datenbank Setup

### 1. PostgreSQL Installation (falls nicht vorhanden)

**Windows:**
- Download von https://www.postgresql.org/download/windows/
- Installiere mit Default-Einstellungen
- Port: 5432
- User: postgres

**Erstelle Trading Database:**
```sql
CREATE DATABASE trading_db;
CREATE USER mt5user WITH PASSWORD '1234';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO mt5user;
```

### 2. Database Initialisierung

**Lokale Datenbank:**
```bash
python scripts/init_database.py --db local
```

**Remote Datenbank:**
```bash
python scripts/init_database.py --db remote
```

**Beide Datenbanken:**
```bash
python scripts/init_database.py --db both
```

### 3. Verbindung testen

```bash
python -c "from src.data.database_manager import get_database; db = get_database('local'); print('✓ Connected' if db.test_connection() else '✗ Failed')"
```

---

## MT5 Setup

### 1. MetaTrader 5 Installation

1. Download MT5 von Broker (z.B. Admirals)
2. Installiere in Standard-Pfad: `C:\Program Files\Admirals Group MT5 Terminal\`
3. Öffne MT5 und logge ein mit Demo-Account

### 2. MT5 Einstellungen

**In MT5 Terminal:**
- Tools → Options → Expert Advisors
  - ☑ Allow algorithmic trading
  - ☑ Allow DLL imports
  - ☑ Allow WebRequest for listed URLs

### 3. MT5 Verbindung testen

```bash
python scripts/test_mt5_connection.py
```

**Erwartete Ausgabe:**
```
====================================================================
MetaTrader 5 Connection Test
====================================================================

### MT5 Configuration ###
Server: admiralsgroup-demo
Login: 42771818
...

✓ MT5 initialized
✓ Login successful
✓ Account Information:
  Balance: 10000.00 EUR
  ...
✓ ALL TESTS PASSED
====================================================================
```

### 4. Symbols aktivieren

Falls Symbols nicht verfügbar sind, aktiviere sie in MT5:
- Market Watch → Right Click → Symbols
- Suche nach EURUSD, GBPUSD, etc.
- Doppelklick um zu aktivieren

---

## System Start

### 1. Pre-Flight Check

```bash
# Config validieren
python -c "from src.utils.config_loader import get_config; get_config().validate(); print('✓ Config valid')"

# MT5 Test
python scripts/test_mt5_connection.py

# Database Test
python scripts/init_database.py --db local
```

### 2. System starten

**Manuell (für Testing):**
```bash
python scripts/start_system.py
```

**Als Windows Service (für Production):**
```bash
# TODO: PM2 oder NSSM Setup
```

### 3. Dashboard öffnen

- **Matrix Dashboard:** http://localhost:5000
- **Analytics:** http://localhost:8501
- **Health Monitor:** http://localhost:8502

---

## Monitoring

### 1. Log Files

```bash
# Live Logs anzeigen
tail -f logs/trading_system.log

# Windows PowerShell
Get-Content logs/trading_system.log -Wait
```

### 2. System Health

**Dashboard:** http://localhost:8502

**CLI:**
```bash
python scripts/system_health_check.py
```

### 3. Database Monitoring

```bash
# Tabellen Status
python -c "from src.data.database_manager import get_database; db = get_database(); print(db.list_tables())"

# Performance Metrics
SELECT * FROM performance_metrics ORDER BY date DESC LIMIT 7;
```

---

## Troubleshooting

### Problem: MT5 Connection Failed

**Symptom:** `MT5 initialization failed`

**Lösung:**
1. Prüfe ob MT5 läuft
2. Prüfe MT5_PATH in .env
3. Prüfe MT5 Login Credentials
4. Prüfe MT5 Settings → Allow algorithmic trading

### Problem: Database Connection Failed

**Symptom:** `Could not connect to database`

**Lösung:**
1. Prüfe ob PostgreSQL läuft:
   ```bash
   # Windows Services
   services.msc → PostgreSQL

   # Linux
   sudo systemctl status postgresql
   ```

2. Prüfe Connection String in .env
3. Prüfe Firewall (Port 5432)
4. Teste Connection:
   ```bash
   psql -h localhost -U mt5user -d trading_db
   ```

### Problem: Module Import Errors

**Symptom:** `ModuleNotFoundError`

**Lösung:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version
python --version  # Should be 3.9+
```

### Problem: Tick Data Not Streaming

**Symptom:** Keine Tick-Daten in Database

**Lösung:**
1. Prüfe MT5 Verbindung
2. Prüfe ob Symbols sichtbar in Market Watch
3. Prüfe Market Hours (Forex: 24/5)
4. Prüfe Logs:
   ```bash
   grep "tick_collector" logs/trading_system.log
   ```

---

## Production Deployment

### 1. Pre-Production Checklist

- [ ] Alle Tests erfolgreich
- [ ] Config Production-ready
- [ ] Database Backups konfiguriert
- [ ] Monitoring aktiv
- [ ] Alerts konfiguriert
- [ ] Auto-Trading = false (initial)
- [ ] Risk Management Settings geprüft

### 2. Database Backup

**Automatisches Backup:**
```bash
# Täglich um 03:00 Uhr
# Windows Task Scheduler / Linux Cron

# Backup Script
pg_dump -h localhost -U mt5user trading_db > backup_$(date +%Y%m%d).sql
```

### 3. Windows Service Setup (NSSM)

```bash
# NSSM installieren
# https://nssm.cc/download

# Service erstellen
nssm install TradingSystem "C:\Projects\alle_zusammen\trading_system_unified\venv\Scripts\python.exe" "C:\Projects\alle_zusammen\trading_system_unified\scripts\start_system.py"

# Service starten
nssm start TradingSystem
```

### 4. Monitoring & Alerts

**Setup Email Alerts:**
- Bei Trading Errors
- Bei System Errors
- Bei großen Verlusten
- Bei ML Model Performance Drop

**Setup SMS Alerts (optional):**
- Kritische System Errors
- Daily Loss Limit erreicht

### 5. Go-Live

**Phase 1: Paper Trading (1-2 Wochen)**
```
ENABLE_AUTO_TRADING=false
- Beobachte Signals
- Validiere Performance
- Fine-tune Settings
```

**Phase 2: Live Trading mit kleinem Kapital**
```
ENABLE_AUTO_TRADING=true
risk_per_trade=0.01  # 1% statt 2%
- Start mit 1000 EUR
- Beobachte 1-2 Wochen
```

**Phase 3: Full Production**
```
ENABLE_AUTO_TRADING=true
risk_per_trade=0.02  # 2%
- Volle Kapitalisierung
- Continuous Monitoring
```

### 6. Wartung

**Täglich:**
- Log Review
- Performance Check
- Open Positions Check

**Wöchentlich:**
- Database Vacuum
- Model Performance Review
- Risk Metrics Review

**Monatlich:**
- Model Retraining
- Strategy Optimization
- System Updates

---

## Support

Bei Problemen:

1. **Logs prüfen:** `logs/trading_system.log`
2. **System Health Check:** `python scripts/system_health_check.py`
3. **MT5 Test:** `python scripts/test_mt5_connection.py`
4. **Database Test:** `python scripts/init_database.py --db local`

---

**Version:** 1.0.0
**Last Updated:** 2025-10-12
**Status:** Ready for Deployment

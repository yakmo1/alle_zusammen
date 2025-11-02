# 🚀 SERVER DEPLOYMENT ANLEITUNG

**Ziel:** Das gleiche System auf dem Remote Server (212.132.105.198) deployen, damit Features korrekt geschrieben werden.

---

## 📋 **Problem-Analyse**

### **LOCAL (Workstation)** ✅
```
bars_eurusd hat:
✅ timestamp, timeframe
✅ open, high, low, close, volume, tick_count
✅ RSI14, MACD, BB_upper, BB_lower, ATR14
❌ Labels (werden separat erstellt)
```

### **REMOTE (Server)** ❌
```
bars_1m hat:
✅ open_time, open, high, low, close, vol_ticks
✅ spread_mean, spread_p95, rv
❌ KEINE Indikatoren (RSI, MACD, ATR, BB)
❌ Anderes Schema
❌ Altes System läuft
```

---

## 🎯 **Lösung: Unified System deployen**

Der Code ist bereits auf GitHub gepusht:
- **Repository:** https://github.com/yakmo1/alle_zusammen.git
- **Branch:** master
- **Letzter Commit:** ec9ba00

---

## 📝 **Deployment-Schritte auf dem Server**

### **1. SSH zum Server**
```bash
ssh user@212.132.105.198
```

### **2. Altes System stoppen (falls läuft)**
```bash
# Check welche Prozesse laufen
ps aux | grep python
ps aux | grep tick
ps aux | grep bar

# Stoppen (PIDs ersetzen)
kill <PID_tick_collector>
kill <PID_bar_aggregator>
```

### **3. Projekt clonen/updaten**
```bash
cd /opt  # oder wo das Projekt hin soll
git clone https://github.com/yakmo1/alle_zusammen.git
cd alle_zusammen/trading_system_unified

# ODER wenn bereits existiert:
cd /pfad/zum/projekt/trading_system_unified
git pull origin master
```

### **4. Python Environment vorbereiten**
```bash
# Python 3.8+ erforderlich
python3 --version

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Falls requirements.txt nicht existiert:
pip install psycopg2-binary pandas numpy MetaTrader5 scikit-learn xgboost lightgbm imbalanced-learn
```

### **5. Config anpassen für Server**
```bash
nano config/config.json
```

**Wichtig ändern:**
```json
{
  "database": {
    "local": {
      "host": "localhost",
      "database": "postgres",   // Nicht "trading_db"!
      "user": "mt5user",
      "password": "1234"
    },
    "active": "local"           // Server nutzt "local" DB
  },
  "mt5": {
    "path": "/pfad/zu/mt5/terminal",  // Linux MT5 Pfad
    "login": YOUR_LOGIN,
    "password": "YOUR_PASSWORD",
    "server": "YOUR_SERVER"
  }
}
```

### **6. Datenbank-Schema aktualisieren**

**Option A: Neue Tabellen erstellen (empfohlen)**
```bash
# Erstelle neue Tabellen mit korrektem Schema
python scripts/setup_database_schema.py
```

**Option B: Alte Tabellen migrieren**
```sql
-- Via psql oder pgAdmin auf Server
ALTER TABLE bars_1m ADD COLUMN rsi14 DOUBLE PRECISION;
ALTER TABLE bars_1m ADD COLUMN macd_main DOUBLE PRECISION;
ALTER TABLE bars_1m ADD COLUMN bb_upper DOUBLE PRECISION;
ALTER TABLE bars_1m ADD COLUMN bb_lower DOUBLE PRECISION;
ALTER TABLE bars_1m ADD COLUMN atr14 DOUBLE PRECISION;
```

### **7. Services starten**

**Terminal 1: Tick Collector**
```bash
cd /pfad/zum/projekt/trading_system_unified
source venv/bin/activate
python scripts/start_tick_collector_v2.py
```

**Terminal 2: Bar Aggregator**
```bash
cd /pfad/zum/projekt/trading_system_unified
source venv/bin/activate
python scripts/start_bar_aggregator_v2.py
```

### **8. Als Systemd Service einrichten (optional, empfohlen)**

**Tick Collector Service:**
```bash
sudo nano /etc/systemd/system/tick-collector.service
```

Inhalt:
```ini
[Unit]
Description=MT5 Tick Collector V2
After=network.target postgresql.service

[Service]
Type=simple
User=mt5user
WorkingDirectory=/opt/alle_zusammen/trading_system_unified
Environment="PATH=/opt/alle_zusammen/trading_system_unified/venv/bin"
ExecStart=/opt/alle_zusammen/trading_system_unified/venv/bin/python scripts/start_tick_collector_v2.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Bar Aggregator Service:**
```bash
sudo nano /etc/systemd/system/bar-aggregator.service
```

Inhalt:
```ini
[Unit]
Description=Bar Aggregator V2
After=network.target postgresql.service

[Service]
Type=simple
User=mt5user
WorkingDirectory=/opt/alle_zusammen/trading_system_unified
Environment="PATH=/opt/alle_zusammen/trading_system_unified/venv/bin"
ExecStart=/opt/alle_zusammen/trading_system_unified/venv/bin/python scripts/start_bar_aggregator_v2.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Services aktivieren:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable tick-collector
sudo systemctl enable bar-aggregator
sudo systemctl start tick-collector
sudo systemctl start bar-aggregator

# Status checken
sudo systemctl status tick-collector
sudo systemctl status bar-aggregator

# Logs ansehen
sudo journalctl -u tick-collector -f
sudo journalctl -u bar-aggregator -f
```

---

## ✅ **Verifikation**

Nach dem Start (nach ~5 Minuten):

```bash
# Python Shell
python3

from src.data.database_manager import get_database

db = get_database('local')

# Check bars structure
result = db.fetch_all("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'bars_eurusd'
""")

for row in result:
    print(row[0])

# Should see: rsi14, macd_main, bb_upper, bb_lower, atr14

# Check latest bar has indicators
bars = db.fetch_all("""
    SELECT timestamp, close, rsi14, macd_main, atr14
    FROM bars_eurusd
    WHERE timeframe = '1m'
    ORDER BY timestamp DESC
    LIMIT 5
""")

for bar in bars:
    print(bar)

# All indicators should have values (not NULL)
```

**Erwartetes Ergebnis:**
```
timestamp                    close    rsi14    macd   atr14
2025-11-02 21:00:00+02:00   1.0875   52.3     0.001  0.0012
2025-11-02 20:59:00+02:00   1.0874   51.8    -0.002  0.0011
...
```

✅ **Alle Indikatoren haben Werte** → System läuft korrekt!

---

## 🔄 **Wartung**

### **Updates pullen:**
```bash
cd /opt/alle_zusammen/trading_system_unified
git pull origin master
sudo systemctl restart tick-collector
sudo systemctl restart bar-aggregator
```

### **Logs ansehen:**
```bash
# Realtime
sudo journalctl -u tick-collector -f
sudo journalctl -u bar-aggregator -f

# Letzte 100 Zeilen
sudo journalctl -u tick-collector -n 100
```

### **Services neu starten:**
```bash
sudo systemctl restart tick-collector
sudo systemctl restart bar-aggregator
```

---

## 📊 **Nach Deployment: Training mit Remote Daten**

Sobald Indikatoren auf dem Server geschrieben werden (nach 24-48h):

```bash
# Auf Workstation (Windows)
cd c:\Projects\alle_zusammen\trading_system_unified
python scripts/train_with_remote_data.py
```

**Erwartung:**
- Mit 21k+ Bars + allen Indikatoren
- ROC-AUC könnte auf 0.70-0.75 steigen
- Viel bessere Performance als V1 (0.645)

---

## 🎯 **Zusammenfassung**

| Schritt | Status | Beschreibung |
|---------|--------|--------------|
| 1. Code auf GitHub | ✅ | Gepusht zu master |
| 2. Server SSH | ⏳ | User muss durchführen |
| 3. Altes System stoppen | ⏳ | User muss durchführen |
| 4. Projekt clonen | ⏳ | `git clone https://github.com/yakmo1/alle_zusammen.git` |
| 5. Config anpassen | ⏳ | database.local.database = "postgres" |
| 6. Dependencies | ⏳ | `pip install -r requirements.txt` |
| 7. Services starten | ⏳ | start_tick_collector_v2.py + start_bar_aggregator_v2.py |
| 8. Verifikation | ⏳ | Check bars haben Indikatoren |

---

## 📞 **Support**

Bei Problemen:
1. Check Logs: `sudo journalctl -u tick-collector -f`
2. Check DB Connection: `psql -h localhost -U mt5user -d postgres`
3. Check MT5 läuft: `ps aux | grep terminal`

---

**Deployment Ready!** 🚀
**Letzte Änderung:** 2025-11-02
**GitHub Commit:** ec9ba00

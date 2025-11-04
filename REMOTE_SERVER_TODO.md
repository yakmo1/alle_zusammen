# 📋 REMOTE SERVER TODO-LISTE
## Automatisierte Datensammlung auf 212.132.105.198

**Erstellt:** 2025-11-04
**Server:** 212.132.105.198:5432
**Ziel:** Datensammlung reaktivieren (gestoppt seit 84 Tagen)

---

## ⚡ SCHNELLSTART (3 Befehle)

```bash
# 1. Setup-Script auf Server kopieren
scp REMOTE_SERVER_SETUP.sh user@212.132.105.198:/tmp/

# 2. SSH zum Server
ssh user@212.132.105.198

# 3. Setup ausführen
chmod +x /tmp/REMOTE_SERVER_SETUP.sh
/tmp/REMOTE_SERVER_SETUP.sh
```

✅ **Fertig!** - Script arbeitet alle Tasks automatisch ab.

---

## 📝 DETAILLIERTE TODO-LISTE

### ✅ TASK 1: System-Voraussetzungen prüfen
**Automatisiert im Script**

**Was wird geprüft:**
- [ ] Python3 installiert (Version 3.8+)
- [ ] Git installiert
- [ ] PostgreSQL Client installiert
- [ ] Pip installiert

**Manuelle Prüfung (optional):**
```bash
python3 --version  # >= 3.8
git --version
psql --version
pip3 --version
```

**Bei Fehlern:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git postgresql-client
```

---

### ✅ TASK 2: Alte Prozesse stoppen
**Automatisiert im Script**

**Was wird gestoppt:**
- [ ] Tick Collector (falls läuft)
- [ ] Bar Aggregator (falls läuft)
- [ ] Feature Calculator (falls läuft)

**Manuelle Prüfung:**
```bash
# Prozesse finden
ps aux | grep tick_collector
ps aux | grep bar_aggregator
ps aux | grep feature

# Stoppen (ersetze <PID>)
kill <PID>

# Oder alle Python-Trading Prozesse:
pkill -f "start_tick_collector"
pkill -f "start_bar_aggregator"
```

---

### ✅ TASK 3: Projekt klonen/aktualisieren
**Automatisiert im Script**

**Ziel-Verzeichnis:** `/opt/alle_zusammen`

**Was passiert:**
- [ ] Prüfe ob Verzeichnis existiert
- [ ] Falls ja: `git pull origin master`
- [ ] Falls nein: `git clone https://github.com/yakmo1/alle_zusammen.git`
- [ ] Berechtigungen setzen

**Manuell (falls Script fehlschlägt):**
```bash
# Option A: Update existierendes Repo
cd /opt/alle_zusammen
git fetch origin
git reset --hard origin/master

# Option B: Neues Clone
sudo rm -rf /opt/alle_zusammen
sudo git clone https://github.com/yakmo1/alle_zusammen.git /opt/alle_zusammen
sudo chown -R $USER:$USER /opt/alle_zusammen
```

**Verifizierung:**
```bash
cd /opt/alle_zusammen
git status
ls -la
```

---

### ✅ TASK 4: Virtual Environment erstellen
**Automatisiert im Script**

**Was passiert:**
- [ ] Altes venv löschen (falls vorhanden)
- [ ] Neues venv erstellen: `python3 -m venv venv`
- [ ] venv aktivieren

**Manuell:**
```bash
cd /opt/alle_zusammen
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

**Verifizierung:**
```bash
which python  # sollte /opt/alle_zusammen/venv/bin/python zeigen
python --version
```

---

### ✅ TASK 5: Dependencies installieren
**Automatisiert im Script**

**Was wird installiert:**
- [ ] psycopg2-binary (PostgreSQL)
- [ ] pandas, numpy
- [ ] MetaTrader5
- [ ] scikit-learn, xgboost, lightgbm
- [ ] flask, flask-socketio
- [ ] python-dotenv, pytz

**Manuell:**
```bash
cd /opt/alle_zusammen
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Oder manuell:
pip install psycopg2-binary pandas numpy MetaTrader5 \
            scikit-learn xgboost lightgbm imbalanced-learn \
            flask flask-socketio python-dotenv pytz
```

**Verifizierung:**
```bash
pip list | grep psycopg2
pip list | grep pandas
pip list | grep MetaTrader5
```

---

### ✅ TASK 6: Konfiguration anpassen
**Automatisiert im Script**

**Datei:** `config/config.json`

**Was wird geändert:**
- [ ] `database.active` → `"local"`
- [ ] `database.local.host` → `"localhost"`
- [ ] `database.local.database` → `"postgres"`
- [ ] `database.local.user` → `"mt5user"`
- [ ] `database.local.password` → `"1234"`

**Manuell:**
```bash
cd /opt/alle_zusammen
nano config/config.json
```

**Korrekte Config:**
```json
{
  "database": {
    "local": {
      "host": "localhost",
      "port": 5432,
      "database": "postgres",
      "user": "mt5user",
      "password": "1234"
    },
    "remote": {
      "host": "212.132.105.198",
      "port": 5432,
      "database": "postgres",
      "user": "mt5user",
      "password": "1234"
    },
    "active": "local"
  }
}
```

**Verifizierung:**
```bash
cat config/config.json | grep -A 5 '"database"'
```

---

### ✅ TASK 7: Datenbank-Verbindung testen
**Automatisiert im Script**

**Was wird geprüft:**
- [ ] Verbindung zu localhost:5432
- [ ] Login mit mt5user/1234
- [ ] Zugriff auf postgres Datenbank
- [ ] Anzahl Bars in bars_1m

**Manuell:**
```bash
# Via psql
psql -h localhost -p 5432 -U mt5user -d postgres -c "SELECT version();"

# Via Python
python3 << 'EOF'
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='postgres',
    user='mt5user',
    password='1234'
)

cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM bars_1m')
count = cur.fetchone()[0]
print(f"Bars in bars_1m: {count:,}")

cur.close()
conn.close()
EOF
```

**Erwartetes Ergebnis:**
```
Bars in bars_1m: 21,088
```

---

### ✅ TASK 8: Datenbank-Schema prüfen
**Automatisiert im Script**

**Was wird geprüft:**
- [ ] Tabelle `bars_1m` existiert
- [ ] Spalten sind korrekt
- [ ] Index auf `open_time` existiert

**Manuell:**
```bash
psql -h localhost -U mt5user -d postgres << 'EOF'

-- Tabellen auflisten
\dt

-- Spalten von bars_1m anzeigen
\d bars_1m

-- Anzahl Bars
SELECT COUNT(*) FROM bars_1m;

-- Neuester Bar
SELECT MAX(open_time) FROM bars_1m;

EOF
```

**Falls Tabelle fehlt (sollte aber existieren):**
```sql
CREATE TABLE IF NOT EXISTS bars_1m (
    id SERIAL PRIMARY KEY,
    open_time TIMESTAMP WITH TIME ZONE NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    vol_ticks BIGINT,
    spread_mean DOUBLE PRECISION,
    spread_p95 DOUBLE PRECISION,
    rv DOUBLE PRECISION,
    UNIQUE(open_time)
);

CREATE INDEX IF NOT EXISTS idx_bars_1m_open_time
ON bars_1m(open_time DESC);
```

---

### ✅ TASK 9: Systemd Services erstellen (OPTIONAL)
**Automatisiert im Script**

**Vorteile:**
- ✅ Automatischer Start beim Server-Neustart
- ✅ Automatischer Restart bei Crash
- ✅ Zentralisiertes Log-Management
- ✅ Einfaches Start/Stop/Status

**Services:**
1. **tick-collector.service** - Sammelt Ticks von MT5
2. **bar-aggregator.service** - Aggregiert Ticks zu Bars

**Manuelle Erstellung:**

```bash
# Tick Collector Service
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
WorkingDirectory=/opt/alle_zusammen
Environment="PATH=/opt/alle_zusammen/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/alle_zusammen/venv/bin/python scripts/start_tick_collector_v2.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/tick-collector.log
StandardError=append:/var/log/tick-collector.error.log

[Install]
WantedBy=multi-user.target
```

```bash
# Bar Aggregator Service
sudo nano /etc/systemd/system/bar-aggregator.service
```

Inhalt:
```ini
[Unit]
Description=Bar Aggregator V2
After=network.target postgresql.service tick-collector.service

[Service]
Type=simple
User=mt5user
WorkingDirectory=/opt/alle_zusammen
Environment="PATH=/opt/alle_zusammen/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/alle_zusammen/venv/bin/python scripts/start_bar_aggregator_v2.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/bar-aggregator.log
StandardError=append:/var/log/bar-aggregator.error.log

[Install]
WantedBy=multi-user.target
```

**Services aktivieren:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable tick-collector
sudo systemctl enable bar-aggregator
```

---

### ✅ TASK 10: Services starten
**Interaktiv im Script**

**Option 1: Systemd (EMPFOHLEN)**

```bash
# Services starten
sudo systemctl start tick-collector
sudo systemctl start bar-aggregator

# Status prüfen
sudo systemctl status tick-collector
sudo systemctl status bar-aggregator

# Logs ansehen (live)
sudo journalctl -u tick-collector -f
sudo journalctl -u bar-aggregator -f
```

**Option 2: Manuell in tmux (Alternative)**

```bash
# Tick Collector
tmux new-session -d -s tick_collector \
  "cd /opt/alle_zusammen && source venv/bin/activate && python scripts/start_tick_collector_v2.py"

# Bar Aggregator
tmux new-session -d -s bar_aggregator \
  "cd /opt/alle_zusammen && source venv/bin/activate && python scripts/start_bar_aggregator_v2.py"

# Sessions ansehen
tmux ls

# An Session anhängen
tmux attach -t tick_collector

# Detach: Ctrl+B dann D
```

**Option 3: Manuell in separaten Terminals**

Terminal 1:
```bash
cd /opt/alle_zusammen
source venv/bin/activate
python scripts/start_tick_collector_v2.py
```

Terminal 2:
```bash
cd /opt/alle_zusammen
source venv/bin/activate
python scripts/start_bar_aggregator_v2.py
```

---

## 🔍 VERIFIZIERUNG

### Nach 5 Minuten: Erste Daten prüfen

```bash
# Prüfe ob Prozesse laufen
ps aux | grep python

# Prüfe neue Bars (letzte Stunde)
psql -h localhost -U mt5user -d postgres -c \
  "SELECT COUNT(*) FROM bars_1m WHERE open_time >= NOW() - INTERVAL '1 hour'"

# Neuester Bar
psql -h localhost -U mt5user -d postgres -c \
  "SELECT MAX(open_time) FROM bars_1m"
```

**Erwartetes Ergebnis:**
- Mindestens 5 neue Bars in letzter Stunde
- Neuester Bar: Timestamp von vor < 5 Minuten

### Nach 1 Stunde: Datenqualität prüfen

```bash
psql -h localhost -U mt5user -d postgres << 'EOF'

-- Statistiken letzte Stunde
SELECT
    COUNT(*) as bars_count,
    MIN(open_time) as first_bar,
    MAX(open_time) as last_bar,
    AVG(vol_ticks) as avg_volume
FROM bars_1m
WHERE open_time >= NOW() - INTERVAL '1 hour';

-- Bars pro Tag (letzte 7 Tage)
SELECT
    DATE(open_time) as tag,
    COUNT(*) as bars
FROM bars_1m
WHERE open_time >= NOW() - INTERVAL '7 days'
GROUP BY DATE(open_time)
ORDER BY tag DESC;

EOF
```

**Erwartetes Ergebnis:**
- ~60 Bars pro Stunde (1-Minuten-Bars)
- ~1440 Bars pro Tag
- Kontinuierliche Datensammlung ohne Lücken

### Nach 24 Stunden: Vollständige Prüfung

```bash
cd /opt/alle_zusammen
source venv/bin/activate
python scripts/data_quality_check.py
```

**Erwartete Ausgabe:**
```
=== BAR DATA QUALITY ===
Total Bars: 22,528+ (21,088 alte + 1,440 neue)
Latest Bar: 2025-11-05 [AKTUELL]
Quality Score: 99.5/100 [EXCELLENT]
Status: ACTIVE - Data collection running
```

---

## 🛠️ TROUBLESHOOTING

### Problem 1: Python-Modul nicht gefunden

**Fehlermeldung:**
```
ModuleNotFoundError: No module named 'psycopg2'
```

**Lösung:**
```bash
cd /opt/alle_zusammen
source venv/bin/activate
pip install psycopg2-binary
```

---

### Problem 2: Database Connection Failed

**Fehlermeldung:**
```
psycopg2.OperationalError: could not connect to server
```

**Lösung:**
```bash
# PostgreSQL läuft?
sudo systemctl status postgresql

# PostgreSQL starten
sudo systemctl start postgresql

# Passwort korrekt?
psql -h localhost -U mt5user -d postgres

# Falls Login fehlschlägt:
sudo -u postgres psql
ALTER USER mt5user WITH PASSWORD '1234';
```

---

### Problem 3: MetaTrader5 import error

**Fehlermeldung:**
```
ModuleNotFoundError: No module named 'MetaTrader5'
```

**Ursache:**
MetaTrader5 Python-Modul funktioniert nur auf Windows!

**Lösung für Linux-Server:**

**Option A:** Code anpassen für Demo-Mode ohne MT5
```bash
nano scripts/start_tick_collector_v2.py
```

Füge Demo-Mode hinzu:
```python
USE_DEMO_MODE = True  # Für Linux-Server

if USE_DEMO_MODE:
    # Nutze historische Daten oder simuliere Ticks
    pass
else:
    import MetaTrader5 as mt5
```

**Option B:** Remote-Tick-Collection (Windows-Maschine sammelt, Linux speichert)
- Windows-Maschine sammelt Ticks
- Sendet via API an Linux-Server
- Linux-Server speichert in PostgreSQL

---

### Problem 4: Services starten nicht

**Symptom:**
```bash
sudo systemctl status tick-collector
# Status: failed
```

**Lösung:**
```bash
# Log ansehen
sudo journalctl -u tick-collector -n 50

# Manuell testen
cd /opt/alle_zusammen
source venv/bin/activate
python scripts/start_tick_collector_v2.py

# Error beheben, dann Service neu starten
sudo systemctl restart tick-collector
```

---

### Problem 5: Keine neuen Daten

**Prüfungen:**

```bash
# 1. Prozesse laufen?
ps aux | grep python

# 2. Logs prüfen
sudo journalctl -u tick-collector -n 100
sudo journalctl -u bar-aggregator -n 100

# 3. Datenbank-Verbindung?
psql -h localhost -U mt5user -d postgres -c "SELECT 1"

# 4. MT5 läuft? (auf Windows)
# Prüfe ob MetaTrader 5 Terminal läuft und eingeloggt ist
```

---

## 📊 MONITORING-BEFEHLE

### Live-Monitoring der Datensammlung

**Bar Count Watch (aktualisiert alle 5 Sekunden):**
```bash
watch -n 5 'psql -h localhost -U mt5user -d postgres -c "SELECT COUNT(*) FROM bars_1m WHERE open_time >= NOW() - INTERVAL '\''1 hour'\''"'
```

**Neuester Bar:**
```bash
watch -n 10 'psql -h localhost -U mt5user -d postgres -c "SELECT MAX(open_time) as neuester_bar FROM bars_1m"'
```

**Service Status:**
```bash
watch -n 5 'systemctl status tick-collector bar-aggregator --no-pager'
```

**Live Logs:**
```bash
# Terminal 1: Tick Collector Log
sudo journalctl -u tick-collector -f

# Terminal 2: Bar Aggregator Log
sudo journalctl -u bar-aggregator -f
```

---

## 🎯 SUCCESS-KRITERIEN

Nach erfolgreichem Setup:

✅ **Sofort (< 5 Minuten):**
- [ ] Services laufen (ps aux | grep python zeigt 2+ Prozesse)
- [ ] Keine Errors in Logs

✅ **Nach 1 Stunde:**
- [ ] ~60 neue Bars in bars_1m
- [ ] Neuester Bar < 2 Minuten alt
- [ ] Kontinuierliche Logs ohne Fehler

✅ **Nach 24 Stunden:**
- [ ] ~1,440 neue Bars (1 Bar pro Minute)
- [ ] Data Quality Score > 95%
- [ ] Keine Service-Restarts/Crashes

✅ **Nach 7 Tagen:**
- [ ] ~10,080 neue Bars
- [ ] Datensammlung läuft stabil
- [ ] Bereit für ML-Training

---

## 📞 SUPPORT

**Bei Problemen:**

1. **Logs prüfen:**
   ```bash
   sudo journalctl -u tick-collector -n 100
   sudo journalctl -u bar-aggregator -n 100
   ```

2. **Datenbank prüfen:**
   ```bash
   psql -h localhost -U mt5user -d postgres
   ```

3. **Manuelle Fehlersuche:**
   ```bash
   cd /opt/alle_zusammen
   source venv/bin/activate
   python -c "from src.data.database_manager import get_database; db = get_database('local'); print(db)"
   ```

---

## ✅ CHECKLISTE

**Vor dem Start:**
- [ ] SSH-Zugang zum Server (212.132.105.198)
- [ ] Git Repository ist aktuell (gepusht auf master)
- [ ] PostgreSQL läuft auf Server
- [ ] User mt5user existiert mit Passwort 1234

**Setup durchführen:**
- [ ] Setup-Script kopiert (REMOTE_SERVER_SETUP.sh)
- [ ] Script ausführbar gemacht (chmod +x)
- [ ] Script ausgeführt
- [ ] Alle 10 Tasks erfolgreich

**Nach Setup:**
- [ ] Services laufen
- [ ] Logs zeigen keine Errors
- [ ] Neue Bars werden erstellt
- [ ] Monitoring läuft

**Nach 24h:**
- [ ] ~1,440 neue Bars vorhanden
- [ ] Datenqualität geprüft
- [ ] System läuft stabil

---

**Ende der TODO-Liste**

*Erstellt: 2025-11-04*
*Für: Remote Server 212.132.105.198*
*Ziel: Reaktivierung der Datensammlung*

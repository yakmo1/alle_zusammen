# 🔧 DATENBANK KONFIGURATION - AKTUALISIERT

**Letzte Aktualisierung:** 2025-11-04 18:58 Uhr
**Status:** ✅ AKTIV - Datensammlung läuft!

---

## 📊 **ZWEI VERSCHIEDENE SYSTEME**

### **System 1: AKTIV ✅ (Production Server)**
```
Host:       212.132.105.198
Database:   trading_db
User:       mt5user
Password:   1234

Tabellen:   bars_eurusd, bars_gbpusd, bars_usdjpy, bars_usdchf, bars_audusd
Schema:     timestamp, timeframe, open, high, low, close, volume, tick_count
            rsi14, macd_main, bb_upper, bb_lower, atr14

Status:     AKTIV - 89,180 Bars, Neueste: 2025-11-04 18:57 Uhr
Wachstum:   ~105 Bars/Stunde/Symbol
```

**Verwendung:**
- Production Server schreibt hier
- Watchdog überwacht diese Datenbank
- ML-Training sollte von hier lesen

**Zugriff:**
```python
import psycopg2

conn = psycopg2.connect(
    host='212.132.105.198',
    port=5432,
    database='trading_db',  # WICHTIG!
    user='mt5user',
    password='1234'
)

# Bars abrufen (1m Timeframe)
cursor = conn.cursor()
cursor.execute("""
    SELECT timestamp, close, rsi14, macd_main
    FROM bars_eurusd
    WHERE timeframe = '1m'
    ORDER BY timestamp DESC
    LIMIT 100
""")
```

---

### **System 2: ALT/LEGACY ❌ (Altes System)**
```
Host:       212.132.105.198
Database:   postgres
User:       mt5user
Password:   1234 (vermutlich)

Tabellen:   bars_1m, bars_5m, bars_5s
Schema:     open_time, open, high, low, close, vol_ticks
            spread_mean, spread_p95, rv

Status:     GESTOPPT seit 12. August 2025
Daten:      21,088 Bars (veraltet)
```

**Verwendung:**
- Altes System (nicht mehr aktiv)
- Historische Daten bis August 2025
- **NICHT für ML-Training verwenden!**

---

## 🔄 **MIGRATION/UMSTELLUNG**

### **Option 1: Weiter mit trading_db (EMPFOHLEN)**

**Vorteile:**
- ✅ System läuft bereits
- ✅ Watchdog überwacht
- ✅ Aktuelle Daten
- ✅ Technische Indikatoren vorhanden

**Änderungen erforderlich:**
- `config/config.json` anpassen
- Alle Scripts auf neue Tabellennamen umstellen
- ML-Training auf `bars_eurusd` statt `bars_1m`

### **Option 2: Zurück zu postgres/bars_1m**

**Nachteile:**
- ❌ Alte Datenbank muss migriert werden
- ❌ Production Server umkonfigurieren
- ❌ Watchdog anpassen
- ❌ Mehr Arbeit

---

## 🛠️ **CONFIG ANPASSEN**

### **Datei: config/config.json**

**ALT (falsch):**
```json
{
  "database": {
    "remote": {
      "host": "212.132.105.198",
      "database": "postgres",      ← FALSCH!
      "user": "mt5user",
      "password": "1234"
    },
    "active": "remote"
  }
}
```

**NEU (korrekt):**
```json
{
  "database": {
    "remote": {
      "host": "212.132.105.198",
      "database": "trading_db",    ← KORREKT!
      "user": "mt5user",
      "password": "1234"
    },
    "active": "remote"
  }
}
```

---

## 📋 **TABELLENSTRUKTUR**

### **bars_eurusd** (und andere Symbole)

```sql
CREATE TABLE bars_eurusd (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    timeframe VARCHAR(5) NOT NULL,           -- '1m', '5m', '15m', '1h', '4h'
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    tick_count INTEGER,

    -- Technische Indikatoren
    rsi14 DOUBLE PRECISION,
    macd_main DOUBLE PRECISION,
    bb_upper DOUBLE PRECISION,
    bb_lower DOUBLE PRECISION,
    atr14 DOUBLE PRECISION,

    UNIQUE(timestamp, timeframe)
);

CREATE INDEX idx_bars_eurusd_timestamp ON bars_eurusd(timestamp DESC);
CREATE INDEX idx_bars_eurusd_timeframe ON bars_eurusd(timeframe, timestamp DESC);
```

### **Daten abfragen**

**Alle 1m Bars (letzte 100):**
```sql
SELECT timestamp, close, rsi14, macd_main, atr14
FROM bars_eurusd
WHERE timeframe = '1m'
ORDER BY timestamp DESC
LIMIT 100;
```

**Bars der letzten 24h:**
```sql
SELECT COUNT(*)
FROM bars_eurusd
WHERE timeframe = '1m'
AND timestamp >= NOW() - INTERVAL '24 hours';
```

**Alle Symbols zusammen:**
```sql
SELECT 'EURUSD' as symbol, COUNT(*) FROM bars_eurusd WHERE timeframe='1m'
UNION ALL
SELECT 'GBPUSD', COUNT(*) FROM bars_gbpusd WHERE timeframe='1m'
UNION ALL
SELECT 'USDJPY', COUNT(*) FROM bars_usdjpy WHERE timeframe='1m'
UNION ALL
SELECT 'USDCHF', COUNT(*) FROM bars_usdchf WHERE timeframe='1m'
UNION ALL
SELECT 'AUDUSD', COUNT(*) FROM bars_audusd WHERE timeframe='1m';
```

---

## 🎯 **ML-TRAINING ANPASSEN**

### **Data Loader aktualisieren**

**ALT:**
```python
def load_training_data():
    query = """
        SELECT open_time, open, high, low, close, vol_ticks
        FROM bars_1m
        ORDER BY open_time DESC
        LIMIT 10000
    """
```

**NEU:**
```python
def load_training_data(symbol='EURUSD', timeframe='1m'):
    table_name = f"bars_{symbol.lower()}"

    query = f"""
        SELECT timestamp, open, high, low, close, volume,
               rsi14, macd_main, bb_upper, bb_lower, atr14
        FROM {table_name}
        WHERE timeframe = %s
        ORDER BY timestamp DESC
        LIMIT 10000
    """

    cursor.execute(query, (timeframe,))
```

---

## 📊 **MONITORING**

### **Python Script (check_active_data.py)**

```bash
# Prüfe aktuelle Datensammlung
python check_active_data.py
```

**Output:**
```
DATENSAMMLUNG STATUS: [AKTIV]
Total Bars:          89,180
Bars letzte Stunde:  525
Qualität:            [EXCELLENT]
```

### **Live Monitoring (alle 60 Sekunden)**

```python
import time
import psycopg2

while True:
    conn = psycopg2.connect(
        host='212.132.105.198',
        database='trading_db',
        user='mt5user',
        password='1234'
    )

    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM bars_eurusd
        WHERE timeframe='1m'
        AND timestamp >= NOW() - INTERVAL '5 minutes'
    """)

    count = cur.fetchone()[0]
    print(f"Neue Bars (letzte 5 min): {count} (erwartet: 5)")

    cur.close()
    conn.close()

    time.sleep(60)
```

---

## ✅ **CHECKLISTE: CONFIG UPDATE**

- [ ] `config/config.json` → `database.remote.database = "trading_db"`
- [ ] `src/data/database_manager.py` → Tabellennamen anpassen
- [ ] `src/ml/data_loader.py` → Query auf `bars_eurusd` statt `bars_1m`
- [ ] `scripts/train_models.py` → Datenbank-Config prüfen
- [ ] Alle Monitoring-Scripts aktualisieren
- [ ] Test: `python check_active_data.py`

---

## 🔗 **VERWANDTE DATEIEN**

- [check_active_data.py](check_active_data.py) - Aktuelle Datensammlung prüfen
- [config/config.json](config/config.json) - Hauptkonfiguration
- [src/data/database_manager.py](src/data/database_manager.py) - Datenbankverbindung

---

## 📞 **SUPPORT**

**Bei Fragen zur neuen Datenbank:**

```bash
# Via psql
psql -h 212.132.105.198 -U mt5user -d trading_db

# Tabellen auflisten
\dt

# Schema einer Tabelle
\d bars_eurusd

# Neueste Bars
SELECT timestamp, close FROM bars_eurusd
WHERE timeframe='1m'
ORDER BY timestamp DESC
LIMIT 10;
```

---

**Letzte Aktualisierung:** 2025-11-04 18:58 Uhr
**Status:** ✅ Produktiv, Datensammlung läuft
**Nächste Prüfung:** Täglich via `check_active_data.py`

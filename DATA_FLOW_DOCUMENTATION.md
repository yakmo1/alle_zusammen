# Data Flow Dokumentation - Trading System

## Übersicht: Wo werden welche Daten gespeichert?

### PostgreSQL Datenbank Details

**Datenbankserver**: PostgreSQL auf `localhost:5432`

**Es gibt ZWEI verschiedene Datenbanken**:

#### 1. Dashboard Datenbank: `autotrading_system`
- **Verwendet von**: Matrix Dashboard (`unified_master_dashboard.py`)
- **User**: `postgres`
- **Konfiguration**: `config/system_config.json`
- **Zweck**: Dashboard-Metriken, Alerts, System-Status

#### 2. Trading Datenbank: `trading_db` ⭐
- **Verwendet von**: Alle Trading-Scripts (Tick Collector, Bar Aggregator, etc.)
- **User**: `mt5user`
- **Konfiguration**: `.env` Datei + `src/utils/config_loader.py`
- **Zweck**: Alle Trading-Daten (Ticks, Bars, Features, Signals, Trades)

---

## Live Data Flow (Aktuell aktiv!)

### 1. Tick Collection (LÄUFT GERADE!)

```
MT5 Live Data
    ↓
[Tick Collector Script]
    ↓ schreibt alle 2 Sekunden (100 Ticks Batches)
PostgreSQL: trading_db
    ↓
Tabelle: ticks_20251013  (täglich neue Tabelle!)
```

**Script**: `scripts/start_tick_collector.py`
**Status**: ✅ AKTIV (Logs zeigen kontinuierliches Schreiben)
**Frequenz**: ~100 Ticks alle 2 Sekunden
**Database**: `trading_db`
**Tabellenname**: `ticks_YYYYMMDD` (z.B. `ticks_20251013` für heute)

**Tabellen-Schema**:
```sql
CREATE TABLE IF NOT EXISTS ticks_20251013 (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,        -- z.B. "EURUSD", "GBPUSD"
    timestamp TIMESTAMP NOT NULL,       -- Tick Zeitstempel
    bid DECIMAL(10, 5) NOT NULL,        -- Bid-Preis
    ask DECIMAL(10, 5) NOT NULL,        -- Ask-Preis
    last DECIMAL(10, 5),                -- Letzter Trade-Preis
    volume BIGINT,                      -- Tick Volume
    time_msc BIGINT                     -- Millisekunden-Timestamp
);

-- Indizes für schnelle Abfragen
CREATE INDEX idx_ticks_20251013_timestamp ON ticks_20251013 (timestamp DESC);
CREATE INDEX idx_ticks_20251013_symbol ON ticks_20251013 (symbol, timestamp DESC);
```

**Aktuelle Daten** (Stand: 13.10.2025 19:42 Uhr):
- Tick Collector läuft seit mehreren Stunden
- Schreibt kontinuierlich Ticks
- Geschätzte Anzahl Ticks heute: 50,000+ (je nach Laufzeit)

**Symbols die gesammelt werden**:
- EURUSD
- GBPUSD
- USDJPY
- AUDUSD
- USDCAD
- EURGBP
- (weitere je nach Config)

---

### 2. Bar Aggregation (Status unklar)

```
PostgreSQL: trading_db / ticks_20251013
    ↓ liest Ticks
[Bar Aggregator Script]
    ↓ aggregiert zu OHLC Bars
PostgreSQL: trading_db
    ↓
Tabelle: bars_eurusd, bars_gbpusd, etc.
```

**Script**: `scripts/start_bar_aggregator.py`
**Status**: ⚠️ LÄUFT, aber unklar ob Daten produziert werden
**Database**: `trading_db`
**Tabellenname**: `bars_{symbol}` (z.B. `bars_eurusd`)

**Erwartetes Schema**:
```sql
CREATE TABLE IF NOT EXISTS bars_eurusd (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    timeframe VARCHAR(5) NOT NULL,      -- "1m", "5m", "15m", "1h", "4h", "1d"
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume BIGINT,
    tick_count INT
);

CREATE INDEX idx_bars_eurusd_timestamp ON bars_eurusd (timestamp DESC, timeframe);
```

**TODO: Verifizieren ob Tabellen existieren und Daten enthalten**

---

### 3. Feature Engineering (Status unklar)

```
PostgreSQL: trading_db / bars_eurusd
    ↓ liest Bars
[Feature Generator Script]
    ↓ berechnet Technical Indicators
PostgreSQL: trading_db
    ↓
Tabelle: features
```

**Script**: `scripts/start_feature_generator.py`
**Status**: ⚠️ LÄUFT, aber unklar ob Daten produziert werden
**Database**: `trading_db`
**Tabellenname**: `features`

**Erwartetes Schema**:
```sql
CREATE TABLE IF NOT EXISTS features (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    timeframe VARCHAR(5) NOT NULL,

    -- Price Features
    close_price DECIMAL(10, 5),

    -- Moving Averages
    ema_9 DECIMAL(10, 5),
    ema_21 DECIMAL(10, 5),
    ema_50 DECIMAL(10, 5),
    ema_200 DECIMAL(10, 5),

    -- Momentum Indicators
    rsi_14 DECIMAL(10, 5),
    rsi_28 DECIMAL(10, 5),
    macd DECIMAL(10, 5),
    macd_signal DECIMAL(10, 5),
    macd_histogram DECIMAL(10, 5),

    -- Volatility
    atr_14 DECIMAL(10, 5),
    bb_upper DECIMAL(10, 5),
    bb_middle DECIMAL(10, 5),
    bb_lower DECIMAL(10, 5),

    -- Volume
    volume BIGINT,
    volume_ma DECIMAL(10, 5),

    -- Time Features
    hour_of_day INT,
    day_of_week INT,

    UNIQUE(symbol, timestamp, timeframe)
);

CREATE INDEX idx_features_timestamp ON features (symbol, timestamp DESC, timeframe);
```

**TODO: Verifizieren ob Tabelle existiert und Daten enthält**

---

### 4. ML Signal Generation (Status unklar)

```
PostgreSQL: trading_db / features
    ↓ liest Features
[Signal Generator Script]
    ↓ lädt ML Model
    ↓ macht Prediction
PostgreSQL: trading_db
    ↓
Tabelle: signals
```

**Script**: `scripts/start_signal_generator.py`
**Status**: ⚠️ LÄUFT, aber wahrscheinlich keine ML Models vorhanden
**Database**: `trading_db`
**Tabellenname**: `signals`

**Erwartetes Schema**:
```sql
CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    signal_type VARCHAR(10) NOT NULL,   -- "BUY", "SELL", "FLAT"
    confidence DECIMAL(5, 4),           -- 0.0000 bis 1.0000
    model_version VARCHAR(50),
    entry_price DECIMAL(10, 5),
    stop_loss DECIMAL(10, 5),
    take_profit DECIMAL(10, 5),
    executed BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMP,
    order_ticket BIGINT
);

CREATE INDEX idx_signals_timestamp ON signals (timestamp DESC);
CREATE INDEX idx_signals_executed ON signals (executed, timestamp DESC);
```

**TODO: Verifizieren ob Signale generiert werden**

---

### 5. Trade Execution (Manuell gesteuert)

```
PostgreSQL: trading_db / signals
    ↓ liest High-Confidence Signals
[Auto Trader] (NOCH NICHT IMPLEMENTIERT!)
    ↓ validiert Risk Management
    ↓ berechnet Position Size
MT5 API: Order Placement
    ↓
Live Trading Account
    ↓ Trade History
PostgreSQL: trading_db
    ↓
Tabelle: trades
```

**Status**: ❌ Automated Trading noch NICHT aktiv
**Database**: `trading_db`
**Tabellenname**: `trades`

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    ticket BIGINT UNIQUE NOT NULL,      -- MT5 Order Ticket
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(10) NOT NULL,    -- "BUY", "SELL"
    volume DECIMAL(10, 2) NOT NULL,     -- Lot Size
    entry_price DECIMAL(10, 5),
    entry_time TIMESTAMP,
    exit_price DECIMAL(10, 5),
    exit_time TIMESTAMP,
    stop_loss DECIMAL(10, 5),
    take_profit DECIMAL(10, 5),
    profit DECIMAL(10, 2),
    swap DECIMAL(10, 2),
    commission DECIMAL(10, 2),
    magic_number BIGINT,
    comment TEXT,
    signal_id BIGINT REFERENCES signals(id)
);

CREATE INDEX idx_trades_entry_time ON trades (entry_time DESC);
CREATE INDEX idx_trades_symbol ON trades (symbol, entry_time DESC);
```

---

## Dashboard Datenbank: `autotrading_system`

**Separate Datenbank für Dashboard-spezifische Daten!**

### Verwendete Tabellen:

#### 1. System Alerts
```sql
CREATE TABLE IF NOT EXISTS system_alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    level VARCHAR(20) NOT NULL,         -- "INFO", "WARNING", "ERROR", "CRITICAL"
    message TEXT NOT NULL,
    source VARCHAR(100),
    acknowledged BOOLEAN DEFAULT FALSE
);
```

#### 2. System Metrics (falls vorhanden)
```sql
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    cpu_percent DECIMAL(5, 2),
    memory_percent DECIMAL(5, 2),
    disk_percent DECIMAL(5, 2),
    mt5_connected BOOLEAN,
    db_connected BOOLEAN
);
```

---

## Data Volume Schätzung (aktuell)

### Ticks (Stand heute)

**Annahme**: Tick Collector läuft seit 8 Stunden

```
Ticks pro Batch: 100
Batches pro Minute: 30 (alle 2 Sekunden)
Minuten pro Stunde: 60
Stunden laufend: 8

Total Ticks = 100 * 30 * 60 * 8 = 1,440,000 Ticks
```

**Speicherplatz pro Tick**: ~100 Bytes
**Total**: ~140 MB für 8 Stunden Tick-Daten

### Bars (falls vorhanden)

**1-Minuten-Bars für 1 Tag**:
- Bars pro Tag: 1440 (24 Stunden * 60 Minuten)
- Pro Symbol: ~1440 Rows
- 6 Symbole: ~8,640 Rows
- Speicherplatz: ~1 MB

### Features (falls vorhanden)

**Features für 1 Tag**:
- Angenommen 20 Features pro Bar
- 1440 Bars * 6 Symbole = 8,640 Feature Rows
- Speicherplatz: ~2 MB

---

## Datenbank-Verbindungsinformationen

### Trading Database (`trading_db`)

**Connection String**:
```
Host: localhost
Port: 5432
Database: trading_db
User: mt5user
Password: [aus .env Datei]
```

**Verwendet von**:
- `scripts/start_tick_collector.py`
- `scripts/start_bar_aggregator.py`
- `scripts/start_feature_generator.py`
- `scripts/start_signal_generator.py`
- `scripts/train_models.py`
- Alle Analyse-Scripts

### Dashboard Database (`autotrading_system`)

**Connection String**:
```
Host: localhost
Port: 5432
Database: autotrading_system
User: postgres
Password: [aus .env Datei]
```

**Verwendet von**:
- `dashboards/matrix_dashboard/unified_master_dashboard.py`

---

## Verification Commands

### 1. Check Tick Data

```bash
# Verbinde zu PostgreSQL
psql -U mt5user -d trading_db

# Prüfe Tabellen
\dt

# Zähle Ticks von heute
SELECT COUNT(*) FROM ticks_20251013;

# Zeige letzte 10 Ticks
SELECT * FROM ticks_20251013 ORDER BY timestamp DESC LIMIT 10;

# Prüfe Timerange
SELECT
    MIN(timestamp) as first_tick,
    MAX(timestamp) as last_tick,
    COUNT(*) as total_ticks
FROM ticks_20251013;

# Prüfe pro Symbol
SELECT
    symbol,
    COUNT(*) as tick_count,
    MIN(timestamp) as first,
    MAX(timestamp) as last
FROM ticks_20251013
GROUP BY symbol;
```

### 2. Check Bar Data

```bash
psql -U mt5user -d trading_db

# Prüfe ob Bars-Tabellen existieren
SELECT tablename
FROM pg_tables
WHERE tablename LIKE 'bars_%';

# Falls bars_eurusd existiert:
SELECT
    timeframe,
    COUNT(*) as bar_count,
    MIN(timestamp) as first_bar,
    MAX(timestamp) as last_bar
FROM bars_eurusd
GROUP BY timeframe;
```

### 3. Check Features

```bash
psql -U mt5user -d trading_db

# Prüfe Features
SELECT COUNT(*) FROM features;

# Wenn Daten vorhanden:
SELECT
    symbol,
    timeframe,
    COUNT(*) as feature_count
FROM features
GROUP BY symbol, timeframe;

# Zeige Sample
SELECT * FROM features ORDER BY timestamp DESC LIMIT 5;
```

### 4. Check Signals

```bash
psql -U mt5user -d trading_db

# Prüfe Signals
SELECT COUNT(*) FROM signals;

# Falls Signals vorhanden:
SELECT
    signal_type,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM signals
WHERE timestamp > NOW() - INTERVAL '1 day'
GROUP BY signal_type;
```

---

## Data Retention Policy

### Tick Data

**Aktuell**: Täglich neue Tabelle (`ticks_YYYYMMDD`)

**Empfohlen**:
- Keep: 30 Tage für Feature Engineering
- Archive: 31-90 Tage (komprimiert)
- Delete: >90 Tage alt

**Cleanup Script benötigt**:
```sql
-- Lösche Tick-Tabellen älter als 30 Tage
DROP TABLE IF EXISTS ticks_20250913;  -- Beispiel
```

### Bar Data

**Empfohlen**: Permanent behalten (relativ kleine Datenmenge)

### Features

**Empfohlen**:
- Keep: 180 Tage für ML Training
- Archive: >180 Tage

### Signals

**Empfohlen**: Permanent behalten für Performance-Analyse

### Trades

**Empfohlen**: Permanent behalten (Steuerrechtliche Gründe!)

---

## Backup Strategy

### Was MUSS gebackupt werden?

1. **Trading Database (`trading_db`)** - KRITISCH!
   - Trades History (für Steuern)
   - Trained ML Models (in DB oder Filesystem)
   - Signals History (Performance-Analyse)

2. **Dashboard Database (`autotrading_system`)** - Optional
   - Alerts/Logs können neu generiert werden

### Backup Befehl

```bash
# Full Backup
pg_dump -U mt5user trading_db > backup_trading_db_$(date +%Y%m%d).sql

# Nur wichtige Tabellen
pg_dump -U mt5user trading_db -t trades -t signals > backup_critical_$(date +%Y%m%d).sql

# Komprimiert
pg_dump -U mt5user trading_db | gzip > backup_trading_db_$(date +%Y%m%d).sql.gz
```

**Empfohlen**: Tägliche Backups, 7 Tage behalten

---

## Nächste Schritte für Data Verification

### Diese Woche:

1. **Verify Tick Collection**
```bash
psql -U mt5user -d trading_db -c "SELECT COUNT(*) FROM ticks_20251013;"
```
✅ Sollte >100,000 Rows zeigen wenn seit 8+ Stunden läuft

2. **Check Bar Aggregator**
```bash
psql -U mt5user -d trading_db -c "\dt bars_*"
```
⚠️ Prüfen ob Tabellen existieren und Daten enthalten

3. **Check Feature Generator**
```bash
psql -U mt5user -d trading_db -c "SELECT COUNT(*) FROM features;"
```
⚠️ Sollte >0 sein wenn Bar Aggregator funktioniert

4. **Monitor Logs**
```bash
# Live Log-Ansicht im Dashboard nutzen!
# Oder:
tail -f trading_system_unified/logs/scripts/bar_aggregator_stdout.log
tail -f trading_system_unified/logs/scripts/feature_generator_stdout.log
```

---

**Letzte Aktualisierung**: 2025-10-13 19:43 Uhr
**Status**: Tick Collection ✅ AKTIV | Bar Aggregation ⚠️ UNKLAR | Features ⚠️ UNKLAR

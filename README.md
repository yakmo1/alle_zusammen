# Trading System Unified

Ein vollautomatisches, KI-gestütztes Trading-System mit Multi-Horizon ML-Forecasting, MetaTrader 5 Integration und Real-time Matrix-Dashboard.

## Übersicht

Dieses System vereint die besten Komponenten aus allen Trading-Projekten zu einem Production-Ready System:

- **Multi-Horizon ML-Forecasting** (30s - 10min Predictions)
- **MetaTrader 5** Integration mit Auto-Reconnect
- **PostgreSQL** Datenbanken (lokal + remote Server)
- **Matrix-Style Dashboard** mit Real-time Updates
- **Kontinuierliches Learning** (Automated Retraining)
- **24/7 Autonomous Trading** mit Risk Management

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
│  Matrix Dashboard  │  Analytics  │  Health Monitor           │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Core Services                            │
│  Trading Engine │ ML Forecasting │ Signal Generator         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  PostgreSQL  │  MT5 Connector  │  Model Storage             │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Machine Learning
- XGBoost + LightGBM Models
- Multi-Horizon Predictions: 30s, 60s, 3min, 5min, 10min
- Walk-forward Cross-Validation
- Automated Daily Retraining
- R² Score >90% Ziel
- Confidence Scoring

### Trading Engine
- Signal Generation aus ML-Forecasts
- Risk Management (2% per Trade)
- Position Sizing
- Stop Loss / Take Profit (dynamisch)
- Daily Loss Limit (5%)
- Max 5 concurrent Trades

### Data Pipeline
- MT5 Tick Streaming
- Bar Aggregation (5s, 1m, 5m, 15m, 1h, 4h, 1d)
- Technical Indicators (SMA, EMA, RSI, MACD, Bollinger, ATR)
- Feature Engineering
- Daily Partitioned Tables

### Dashboards
1. **Matrix Master Dashboard** (Flask + SocketIO)
   - Real-time Trading View
   - System Monitoring
   - Database Analytics
   - Alert Management

2. **Analytics Dashboard** (Streamlit)
   - Model Performance Metrics
   - Accuracy Charts
   - Feature Importance

3. **Health Monitor** (Streamlit)
   - System Component Status
   - Error Tracking
   - Performance Monitoring

## Installation

### Voraussetzungen
- Python 3.9+
- PostgreSQL 13+
- MetaTrader 5 (lokal installiert)

### Setup

1. **Repository klonen**
```bash
cd trading_system_unified
```

2. **Virtual Environment erstellen**
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
```

3. **Dependencies installieren**
```bash
pip install -r requirements.txt
```

4. **Konfiguration anpassen**
- `.env` bearbeiten (MT5 Credentials, DB Settings)
- `config/config.json` prüfen

5. **Datenbank initialisieren**
```bash
python scripts/init_database.py
```

6. **MT5 Verbindung testen**
```bash
python scripts/test_mt5_connection.py
```

## Usage

### System starten
```bash
python scripts/start_system.py
```

Dies startet:
- Tick Collector (MT5 → PostgreSQL)
- Bar Builder (Tick Aggregation)
- Feature Calculator
- ML Inference Engine
- Trading Engine
- Matrix Dashboard (http://localhost:5000)
- Analytics Dashboard (http://localhost:8501)
- Health Monitor (http://localhost:8502)

### Einzelne Komponenten starten

**Matrix Dashboard**
```bash
python dashboards/matrix_dashboard/unified_master_dashboard.py
```

**Model Training**
```bash
python scripts/train_models.py
```

**Model Management**
```bash
python scripts/manage_models.py list
python scripts/manage_models.py activate <model_id>
```

### System stoppen
```bash
python scripts/stop_system.py
```

## Projektstruktur

```
trading_system_unified/
├── src/
│   ├── ml/                 # Machine Learning Models
│   ├── data/               # Data Pipeline
│   ├── connectors/         # MT5, Database Connectors
│   ├── strategies/         # Trading Strategies
│   ├── core/               # Trading Engine
│   └── utils/              # Utilities
├── dashboards/
│   ├── matrix_dashboard/   # Matrix Master Dashboard
│   ├── analytics/          # Streamlit Analytics
│   └── health_monitor/     # System Health
├── scripts/
│   ├── start_system.py     # System Orchestrator
│   ├── train_models.py     # ML Training
│   └── manage_models.py    # Model Management
├── config/
│   ├── config.json         # Main Configuration
│   └── .env                # Environment Variables
├── tests/                  # Unit & Integration Tests
├── docs/                   # Documentation
├── alembic/                # Database Migrations
├── logs/                   # Log Files
└── models/                 # Trained ML Models
```

## Konfiguration

### Database
- **Lokal**: localhost:5432/trading_db
- **Remote**: 212.132.105.198:5432/postgres
- Active: `local` (in config.json)

### MT5
- Server: admiralsgroup-demo
- Account: 42771818

### Trading
- Symbols: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD
- Base Timeframe: 1m
- Risk per Trade: 2%
- Max Daily Loss: 5%

### ML Models
- Algorithms: XGBoost, LightGBM
- Horizons: 30s, 60s, 3min, 5min, 10min
- Min Confidence: 60%
- Retraining: Daily (nightly)

## Monitoring

### Dashboards
- Matrix Dashboard: http://localhost:5000
- Analytics: http://localhost:8501
- Health Monitor: http://localhost:8502

### Logs
- Location: `logs/trading_system.log`
- Level: INFO (konfigurierbar in .env)
- Rotation: 10MB, 5 Backups

### Alerts
- System Errors
- Trading Signals
- Model Performance Issues
- Database Connection Problems

## Development

### Testing
```bash
pytest tests/
```

### Code Quality
```bash
black src/
flake8 src/
mypy src/
```

### Database Migrations
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Deployment

Siehe [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) für detaillierte Deployment-Anweisungen.

## Roadmap

- [x] Phase 1: Projektstruktur & Foundation
- [ ] Phase 2: Datenbank-Setup
- [ ] Phase 3: MT5 Integration
- [ ] Phase 4: ML System
- [ ] Phase 5: Trading Engine
- [ ] Phase 6: Dashboard System
- [ ] Phase 7: System Orchestration
- [ ] Phase 8: Testing & Validation
- [ ] Phase 9: Deployment & Go-Live

## Contributing

Dieses ist ein privates Trading-System. Keine externen Contributions.

## License

Proprietary - Alle Rechte vorbehalten

## Support

Bei Fragen oder Problemen, siehe [docs/](docs/) oder kontaktiere den Entwickler.

---

**Version:** 1.0.0
**Status:** In Development
**Last Updated:** 2025-10-12

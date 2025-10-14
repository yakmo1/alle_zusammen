# Machine Learning System - Quick Start Guide

## Übersicht

Das ML-System besteht aus drei Hauptkomponenten:
1. **Model Trainer** - Trainiert Multi-Horizon Forecasting Models
2. **Inference Engine** - Macht Real-time Predictions
3. **Signal Generator** - Generiert Trading Signals aus Predictions

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Data Pipeline                          │
│   Tick Collector → Bar Builder → Feature Calculator     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  ML Training                             │
│   Model Trainer (XGBoost + LightGBM)                    │
│   → Multi-Horizon Models (30s, 60s, 3m, 5m, 10m)       │
│   → Saved to models/ directory                          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  ML Inference                            │
│   Inference Engine → Predictions every 10s              │
│   → Stored in model_forecasts table                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Signal Generation                           │
│   Signal Generator → Consensus Signals                  │
│   → Multi-Horizon Analysis                              │
│   → Confidence & Agreement Filtering                    │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Daten sammeln

Zuerst müssen genug Daten vorhanden sein:

```bash
# Terminal 1: Tick Collector starten
cd trading_system_unified
python src/data/tick_collector.py

# Mindestens 1-2 Tage laufen lassen für Training
```

### 2. Models trainieren

```bash
# Alle Models trainieren (empfohlen)
python scripts/train_models.py

# Einzelnes Model trainieren
python scripts/train_models.py --symbol EURUSD --timeframe 1m --horizon 60 --algorithm xgboost

# Nur XGBoost (schneller)
python scripts/train_models.py --algorithm xgboost
```

**Training Outputs:**
- Models werden in `models/` gespeichert
- Model Info wird in `model_versions` Tabelle gespeichert
- Training Metrics (R², RMSE, MAE) werden geloggt

**Beispiel Output:**
```
Training model 1/30: EURUSD 1m 60s xgboost
Model trained: R2=0.9234, RMSE=0.000123
Model saved to models/EURUSD_1m_60s_xgboost.joblib
```

### 3. Inference starten

```bash
# Kontinuierliche Predictions (empfohlen)
python scripts/run_inference.py

# Einmalige Predictions (zum Testen)
python scripts/run_inference.py --once

# Nur für EURUSD
python scripts/run_inference.py --symbol EURUSD --timeframe 1m
```

**Inference Outputs:**
- Predictions werden in `model_forecasts` Tabelle gespeichert
- Läuft alle 10 Sekunden (konfigurierbar mit `--interval`)

### 4. Signals generieren

```python
from src.core.signal_generator import SignalGenerator

generator = SignalGenerator()

# Signal für ein Symbol generieren
signal = generator.generate_signal('EURUSD', '1m')

if signal:
    print(f"{signal['signal']} @ {signal['entry_price']}")
    print(f"SL: {signal['stop_loss']}, TP: {signal['take_profit']}")
    print(f"Confidence: {signal['confidence']:.3f}")
```

## Configuration

### Model Training Parameters

In `src/ml/model_trainer.py`:

```python
# Horizons (in Sekunden)
self.horizons = [30, 60, 180, 300, 600]  # 30s, 1m, 3m, 5m, 10m

# Algorithms
self.algorithms = ['xgboost', 'lightgbm']

# Timeframes
self.timeframes = ['1m', '5m', '15m']
```

### XGBoost Parameters

```python
model = xgb.XGBRegressor(
    n_estimators=200,      # Anzahl Trees
    learning_rate=0.05,    # Learning Rate
    max_depth=6,           # Max Tree Depth
    subsample=0.8,         # Sampling Ratio
    colsample_bytree=0.8   # Feature Sampling
)
```

### Signal Generation Parameters

In `src/core/signal_generator.py`:

```python
self.min_confidence = 0.60            # Min 60% Confidence
self.min_agreement_ratio = 0.6        # 60% Horizons müssen übereinstimmen

# Horizon Weights
self.horizon_weights = {
    30: 0.5,   # 30s: 50% Gewicht
    60: 0.7,   # 1m: 70% Gewicht
    180: 1.0,  # 3m: 100% Gewicht
    300: 1.0,  # 5m: 100% Gewicht
    600: 0.8   # 10m: 80% Gewicht
}
```

## Database Tables

### model_versions
Speichert Model Metadaten:
- `model_name`: z.B. "EURUSD_1m_60s"
- `version`: Model Version
- `algorithm`: 'xgboost' oder 'lightgbm'
- `metrics`: JSON mit Training Metrics
- `is_active`: Aktiv/Inaktiv Flag

### model_forecasts
Speichert Predictions:
- `symbol`, `timeframe`, `prediction_horizon`
- `current_price`, `predicted_price`
- `signal`: BUY/SELL/HOLD
- `confidence`: 0-1
- `algorithm`, `model_version`

### signals
Speichert Trading Signals:
- `symbol`, `timeframe`
- `signal_type`: BUY/SELL
- `entry_price`, `stop_loss`, `take_profit`
- `confidence`, `risk_reward_ratio`
- `status`: ACTIVE/EXECUTED/CANCELLED

## Feature Engineering

Verwendete Features:

### Technical Indicators
- **SMA** (10, 20, 50 period)
- **EMA** (10, 20 period)
- **RSI** (14 period)
- **MACD** (12, 26, 9)
- **Bollinger Bands** (20, 2 std)
- **ATR** (14 period)

### Price Features
- `price_change_1`: 1-bar % change
- `price_change_5`: 5-bar % change
- `price_change_10`: 10-bar % change

### Target Variables
- `target_Ns`: Future price in N seconds
- `direction_Ns`: Direction (up=1, down=0)

## Performance Metrics

### Model Metrics
- **R² Score**: Coefficient of Determination (Ziel: >0.90)
- **RMSE**: Root Mean Squared Error
- **MAE**: Mean Absolute Error

### Signal Quality
- **Confidence**: Model-basierte Confidence (0-1)
- **Agreement Ratio**: % der Horizons die übereinstimmen
- **Risk/Reward Ratio**: TP/SL Ratio (default: 1.5)

## Monitoring

### Check Model Performance

```sql
-- Beste Models nach R² Score
SELECT model_name, algorithm,
       (metrics->>'test_r2')::float as r2_score
FROM model_versions
WHERE is_active = true
ORDER BY r2_score DESC
LIMIT 10;
```

### Check Recent Predictions

```sql
-- Letzte Predictions
SELECT symbol, timeframe, prediction_horizon,
       signal, confidence,
       current_price, predicted_price
FROM model_forecasts
WHERE timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC
LIMIT 20;
```

### Check Active Signals

```sql
-- Aktive Signals
SELECT symbol, signal_type, entry_price,
       stop_loss, take_profit,
       confidence, timestamp
FROM signals
WHERE status = 'ACTIVE'
ORDER BY timestamp DESC;
```

## Troubleshooting

### Problem: "No models loaded"

**Lösung:** Models müssen zuerst trainiert werden:
```bash
python scripts/train_models.py
```

### Problem: "No predictions available"

**Lösung 1:** Inference Engine muss laufen:
```bash
python scripts/run_inference.py
```

**Lösung 2:** Nicht genug Features vorhanden - Data Pipeline muss laufen:
```bash
# Tick Collector
python src/data/tick_collector.py

# Bar Builder
python src/data/bar_builder.py

# Feature Calculator
python src/data/feature_calculator.py
```

### Problem: "Signal confidence too low"

**Lösung:** Models neu trainieren mit mehr Daten, oder Confidence Threshold senken:
```python
# In signal_generator.py
self.min_confidence = 0.50  # von 0.60 auf 0.50
```

### Problem: Training dauert zu lange

**Lösung 1:** Nur XGBoost verwenden (schneller als LightGBM):
```bash
python scripts/train_models.py --algorithm xgboost
```

**Lösung 2:** Weniger Horizons trainieren:
```python
# In model_trainer.py
self.horizons = [60, 300]  # Nur 1m und 5m
```

## Best Practices

### Model Training

1. **Mindestens 7 Tage Daten** sammeln vor Training
2. **Wöchentlich neu trainieren** (Sonntag, wenn Märkte geschlossen)
3. **Models vergleichen**: XGBoost vs LightGBM
4. **Metrics überwachen**: R² Score sollte >0.85 sein

### Inference

1. **Models vorher laden** (nicht bei jedem Prediction neu laden)
2. **Interval anpassen**: 10s für 1m, 30s für 5m timeframe
3. **Monitoring**: Prediction Latenz sollte <1s sein

### Signal Generation

1. **Multi-Horizon Analysis** nutzen (nicht nur ein Horizon)
2. **Confidence Threshold** konservativ halten (>0.60)
3. **Agreement Ratio** prüfen (>0.60 bedeutet klarer Trend)

## Next Steps

1. ✅ Models trainieren
2. ✅ Inference starten
3. ✅ Signal Generation testen
4. ⏳ Order Executor implementieren
5. ⏳ Backtesting System aufbauen
6. ⏳ Paper Trading starten

## Support

Bei Problemen:
1. Logs prüfen: `logs/trading_system.log`
2. Database prüfen: PostgreSQL Tables
3. Health Check: `python scripts/system_health_check.py`

---

**Version:** 1.0.0-beta
**Date:** 2025-10-12
**Status:** Ready for Testing

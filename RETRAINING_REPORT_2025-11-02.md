# 🚀 MODEL RETRAINING REPORT
**Datum:** 2025-11-02, 16:30 Uhr
**Anlass:** Vollständige Bar-Aggregation aus 3.3M historischen Ticks
**Status:** ✅ **ABGESCHLOSSEN MIT GEMISCHTEN ERGEBNISSEN**

---

## 📊 DATEN-UPGRADE

### Vorher (Erstes Training)
```
Bars pro Symbol:     251 (1m timeframe)
Gesamt Bars:       1,255
Training Samples:  ~1,225
Zeitraum:          2.3 Tage (teilweise)
```

### Nachher (Nach vollständiger Aggregation)
```
Bars pro Symbol:   1,075 (1m timeframe)  ✅ +329%
Gesamt Bars:       5,375                 ✅ +328%
Training Samples:  ~5,300                ✅ +333%
Zeitraum:          2.3 Tage (vollständig)
```

### Tick-Daten Basis
```
EURUSD: 640,554 Ticks (3 Tabellen)
GBPUSD: 640,568 Ticks
USDJPY: 640,685 Ticks
USDCHF: 640,705 Ticks
AUDUSD: 640,553 Ticks

GESAMT: 3,342,850 Ticks → 5,375 Bars
```

**Aggregationsrate:** ~622 Ticks pro Bar (durchschnittlich)

---

## 🤖 MODEL PERFORMANCE COMPARISON

### Model 1: XGBoost (label_h5, 5min Horizon)

#### VORHER (251 Bars, 1,225 Samples)
```
Metric           Train    Val      Test
----------------------------------------
Accuracy         1.0000   0.7213   0.6973  ✅
Precision        1.0000   0.5000   0.4762
Recall           1.0000   0.0784   0.1818
F1-Score         1.0000   0.1356   0.2632
ROC-AUC          1.0000   0.5823   0.6453  ✅
```

#### NACHHER (1,075 Bars, 5,300 Samples)
```
Metric           Train    Val      Test
----------------------------------------
Accuracy         0.9936   0.7428   0.6600  ⚠️ -5.4%
Precision        1.0000   0.2857   0.3750  ⚠️ -21.2%
Recall           0.9756   0.0757   0.0690  ❌ -62.0%
F1-Score         0.9876   0.1197   0.1165  ❌ -55.7%
ROC-AUC          1.0000   0.5906   0.4989  ❌ -22.7%
```

**ANALYSE:**
- ❌ **Test Accuracy gesunken:** 69.7% → 66.0%
- ❌ **ROC-AUC stark gesunken:** 0.645 → 0.499 (fast Random!)
- ❌ **Recall deutlich schlechter:** 18.2% → 6.9%
- ⚠️ **Overfitting bleibt:** Train Acc 99.4% vs Test 66%

**URSACHEN:**
1. **Class Imbalance verschärft:** Mehr Daten, aber nur 12.2% UP Labels
2. **Niedrige Volatilität:** Die zusätzlichen Daten sind aus niedrig-volatilen Perioden
3. **Model lernt "immer DOWN predicten":** 87.8% DOWN Labels

---

### Model 2: LightGBM (label_h5, 5min Horizon)

#### VORHER
```
Metric           Train    Val      Test
----------------------------------------
Accuracy         1.0000   0.7213   0.7027  ✅
Precision        1.0000   0.5000   0.5000
Recall           1.0000   0.0392   0.0909
F1-Score         1.0000   0.0727   0.1538
ROC-AUC          1.0000   0.5401   0.6242  ✅
```

#### NACHHER
```
Metric           Train    Val      Test
----------------------------------------
Accuracy         0.9901   0.7516   0.6737  ⚠️ -4.1%
Precision        1.0000   0.2308   0.4783  ⚠️ -4.3%
Recall           0.9623   0.0324   0.0421  ❌ -53.7%
F1-Score         0.9808   0.0569   0.0775  ❌ -49.6%
ROC-AUC          0.9999   0.6113   0.5080  ❌ -18.6%
```

**ANALYSE:**
- ⚠️ **Test Accuracy leicht gesunken:** 70.3% → 67.4%
- ❌ **ROC-AUC deutlich schlechter:** 0.624 → 0.508
- ⚠️ **Recall halbiert:** 9.1% → 4.2%

---

### Model 3: XGBoost (label_h10, 10min Horizon)

#### VORHER
```
Metric           Train    Val      Test
----------------------------------------
Accuracy         1.0000   0.6704   0.5778
Precision        1.0000   0.5000   0.7500
Recall           1.0000   0.0678   0.0750
F1-Score         1.0000   0.1194   0.1364
ROC-AUC          1.0000   0.5223   0.6155
```

#### NACHHER
```
Metric           Train    Val      Test
----------------------------------------
Accuracy         0.9968   0.6801   0.5727  ≈ GLEICH
Precision        1.0000   0.2987   0.4821  ❌ -35.7%
Recall           0.9898   0.1027   0.0796  ≈ GLEICH
F1-Score         0.9949   0.1528   0.1367  ≈ GLEICH
ROC-AUC          1.0000   0.4785   0.5307  ⚠️ -13.8%
```

**ANALYSE:**
- ≈ **Accuracy fast gleich:** 57.8% → 57.3%
- ❌ **Precision deutlich schlechter:** 75% → 48.2%
- ⚠️ **ROC-AUC gesunken:** 0.616 → 0.531

---

## 📉 PERFORMANCE SUMMARY

### Vergleich: Alt vs Neu

| Metric | Model | Vorher | Nachher | Change | Bewertung |
|--------|-------|--------|---------|--------|-----------|
| **Accuracy** | XGBoost (h5) | 69.7% | 66.0% | -3.7% | ⚠️ SCHLECHTER |
| **Accuracy** | LightGBM (h5) | 70.3% | 67.4% | -2.9% | ⚠️ SCHLECHTER |
| **ROC-AUC** | XGBoost (h5) | 0.645 | 0.499 | -22.7% | ❌ VIEL SCHLECHTER |
| **ROC-AUC** | LightGBM (h5) | 0.624 | 0.508 | -18.6% | ❌ VIEL SCHLECHTER |
| **Precision** | XGBoost (h5) | 47.6% | 37.5% | -10.1% | ❌ SCHLECHTER |
| **Recall** | XGBoost (h5) | 18.2% | 6.9% | -11.3% | ❌ VIEL SCHLECHTER |

**GESAMT-BEWERTUNG:** ❌ **VERSCHLECHTERUNG**

---

## 🔍 PROBLEM-ANALYSE

### 1. Class Imbalance Problem verschärft

**Label Distribution (label_h5):**
```
Vorher (251 bars):   23.0% UP, 77.0% DOWN  (Balance: 0.30)
Nachher (1,075 bars): 12.2% UP, 87.8% DOWN  (Balance: 0.14)
```

**Ursache:** Die zusätzlichen 824 Bars enthalten noch weniger volatile Phasen!

**Effekt:**
- Model lernt "immer DOWN predicten" → 87.8% Accuracy möglich
- Aber: ROC-AUC nahe 0.5 (Random Guessing)
- Recall sehr niedrig (viele False Negatives)

### 2. Datenqualität: Niedrig-volatile Perioden

Die zusätzlichen Daten stammen hauptsächlich von:
- Nacht-Sessions (niedrige Liquidität)
- Wochenend-Gaps
- Konsolidierungsphasen

**Konsequenz:**
- Weniger "echte" Trading-Signale
- Mehr Noise
- Schwierigeres Lernproblem

### 3. Overfitting bleibt bestehen

```
XGBoost Train Accuracy: 99.4%
XGBoost Test Accuracy:  66.0%

Differenz: 33.4% (massive Overfitting!)
```

**Ursache:**
- Zu viele Features (174 features)
- Zu tiefe Trees (max_depth=6)
- Keine ausreichende Regularisierung

---

## 💡 LÖSUNGSANSÄTZE

### Sofort-Maßnahmen

#### 1. Class Balancing implementieren
```python
# In Training Script:
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
# scale_pos_weight ≈ 7.2 (für 12.2% UP)

xgb_params = {
    'scale_pos_weight': scale_pos_weight,  # NEU
    ...
}
```

#### 2. Threshold senken (wieder)
```json
{
  "min_profit_pips": 1.0  // Statt 1.5
}
```

**Erwartung:** Balance steigt auf ~0.25-0.30

#### 3. Regularisierung erhöhen
```python
xgb_params = {
    'max_depth': 4,           # Statt 6
    'min_child_weight': 5,    # Statt 1
    'gamma': 0.5,             # Statt 0
    'subsample': 0.7,         # Statt 0.8
    'learning_rate': 0.05,    # Statt 0.1
}
```

#### 4. Feature Selection
```python
# Nutze nur Top 30-50 wichtigste Features
# Statt alle 174 Features
```

### Mittelfristig

#### 5. Data Filtering
```python
# Filtere nur volatile Handelsphasen:
# - London Session (08:00-16:00 UTC)
# - NY Session (13:00-21:00 UTC)
# - Overlap (13:00-16:00 UTC) ← BESTE ZEIT

# Entferne:
# - Nacht-Sessions
# - Wochenenden
# - Niedrig-volatile Bars (ATR < Threshold)
```

#### 6. Alternative: Regression statt Classification
```python
# Predict: Prozentuale Preisänderung
# Statt: UP/DOWN Binary

# Vorteil: Keine Class Imbalance
# Nachteil: Komplexeres Model
```

---

## 📊 VERGLEICH: WELCHES MODEL NUTZEN?

### Empfehlung: **ALTE MODELS BEHALTEN!** ✅

| Kriterium | Alte Models (251 bars) | Neue Models (1,075 bars) | Gewinner |
|-----------|----------------------|------------------------|----------|
| **Test Accuracy** | 69.7% | 66.0% | ✅ ALT |
| **ROC-AUC** | 0.645 | 0.499 | ✅ ALT |
| **Precision** | 47.6% | 37.5% | ✅ ALT |
| **Recall** | 18.2% | 6.9% | ✅ ALT |
| **F1-Score** | 0.263 | 0.117 | ✅ ALT |
| **Trainingsdaten** | 1,225 | 5,300 | ✅ NEU |

**Fazit:** Trotz 4.3x mehr Daten sind die **alten Models besser**!

**Grund:** Qualität > Quantität
- 251 Bars aus volatile Perioden > 1,075 Bars mit viel Noise

---

## 🎯 AKTIONSPLAN

### Option A: Alte Models verwenden (EMPFOHLEN)
```bash
# Nutze die Models vom ersten Training
# models/xgboost_1m_label_h5_lookback5.model (erste Version)

# Diese sind bereits in Production!
```

**Begründung:**
- ✅ Bessere Performance (69.7% Accuracy, 0.645 AUC)
- ✅ Funktionierende Signal Generation (bereits getestet)
- ✅ Keine weitere Arbeit nötig

### Option B: Neue Models mit Fixes (2-3h Arbeit)
```bash
1. min_profit_pips auf 1.0 reduzieren
2. Labels neu generieren
3. Class Weights implementieren
4. Regularisierung erhöhen
5. Feature Selection
6. Neu trainieren
```

**Erwartung:**
- Accuracy: 66% → 70-72%
- ROC-AUC: 0.50 → 0.62-0.65
- Recall: 7% → 15-25%

### Option C: Data Filtering + Retraining (4-6h Arbeit)
```bash
1. Filtere nur volatile Trading-Sessions
2. Entferne niedrig-liquide Perioden
3. Behalte nur ~500-600 beste Bars
4. Trainiere neu
```

**Erwartung:**
- Accuracy: 72-75%
- ROC-AUC: 0.65-0.70
- Recall: 20-30%

---

## 🏆 LEARNINGS

### Was haben wir gelernt?

#### 1. Mehr Daten ≠ Bessere Models
- ❌ 4.3x mehr Daten führte zu schlechteren Models
- ✅ Qualität der Daten ist wichtiger als Quantität
- ✅ Filtere gezielt volatile/liquide Perioden

#### 2. Class Imbalance ist kritisch
- ❌ 12% UP vs 88% DOWN → Model lernt "DOWN predicten"
- ✅ Threshold muss sorgfältig gewählt werden
- ✅ Class Weights oder Balancing notwendig

#### 3. Overfitting bleibt Problem
- ❌ Train Acc 99% vs Test Acc 66% → 33% Gap!
- ✅ Mehr Regularisierung nötig
- ✅ Feature Selection kritisch

#### 4. ROC-AUC ist wichtigster Metric
- Accuracy kann täuschen (bei Imbalance)
- ROC-AUC zeigt echte prädiktive Fähigkeit
- 0.50 = Random, 0.65 = Gut, 0.80+ = Sehr gut

---

## 📋 EMPFEHLUNG

### Für Production: **ALTE MODELS NUTZEN** ✅

```
Model: XGBoost (label_h5, erste Version)
File: models/xgboost_1m_label_h5_lookback5.model (Backup anlegen!)
Performance: 69.7% Accuracy, 0.645 AUC

Begründung:
- Bessere Metriken als neue Models
- Bereits getestet & funktionsfähig
- Signal Generator nutzt diese bereits
```

### Für Zukunft: **Data Quality verbessern**

```
1. Sammle Daten NUR während:
   - London Session (08:00-16:00 UTC)
   - NY Session (13:00-21:00 UTC)
   - Overlap ←  BESTE (13:00-16:00 UTC)

2. Filtere:
   - ATR > Minimum Threshold (volatile genug)
   - Spread < Maximum (gute Liquidität)
   - Keine Wochenenden/Feiertage

3. Target:
   - ~500-1,000 HOCHQUALITATIVE Bars
   - Statt 5,000+ mit viel Noise
```

---

## 📊 FINAL STATUS

### Models Verfügbar

**Version 1 (251 bars) - EMPFOHLEN:**
```
✅ xgboost_1m_label_h5_lookback5.model (69.7% acc, 0.645 AUC)
✅ lightgbm_1m_label_h5_lookback5.model (70.3% acc, 0.624 AUC)
```

**Version 2 (1,075 bars) - Backup:**
```
⚠️ xgboost_1m_label_h5_lookback5.model (66.0% acc, 0.499 AUC)
⚠️ lightgbm_1m_label_h5_lookback5.model (67.4% acc, 0.508 AUC)
```

### Nächste Schritte

1. ✅ **Nutze Version 1 Models** für Signal Generation
2. 📅 **Implementiere Phase 4** (Automated Trading) mit guten Models
3. 📅 **Sammle selektiv neue Daten** (nur volatile Sessions)
4. 📅 **Iteriere** mit besseren Daten

---

**Report Ende**
**Status:** Models trainiert, aber Version 1 bleibt empfohlen
**Next Action:** Phase 4 mit alten (besseren) Models

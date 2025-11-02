# PHASE 2: ML SYSTEM IMPLEMENTATION PLAN

**Prerequisites:** ✅ Phase 1 Complete (Data Quality: 99.7/100)
**Start Date:** 2025-10-14
**Status:** Ready to Start

---

## Overview

Phase 2 builds the machine learning system that will generate trading signals from the high-quality data produced by Phase 1.

### Key Objectives
1. Design and implement ML model architecture
2. Create label engineering system for multi-horizon predictions
3. Build training pipeline with XGBoost and LightGBM
4. Implement feature selection and optimization
5. Create model versioning and persistence system

---

## Data Available for Training

### Input Data Sources
- **Tick Data:** 73,250 ticks across 5 symbols with 16 indicators
- **Bar Data:** 31+ bars per symbol across 5 timeframes (1m, 5m, 15m, 1h, 4h)
- **Timeframes:** 1m, 5m, 15m, 1h, 4h
- **Symbols:** EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD

### Available Features (Per Bar)
**Price Features:**
- open, high, low, close, volume, tick_count

**Technical Indicators:**
- Trend: ma14, ma50, ema14, ema50, wma14, wma50
- Momentum: rsi14, macd_main, macd_signal, macd_hist
- Volatility: bb_upper, bb_middle, bb_lower, atr14, stddev14
- Other: adx14, cci14, momentum14

**Total Features per Bar:** 25 columns

---

## Phase 2 Components

### 2.1 Model Architecture Design

**Goal:** Define ML pipeline structure

**Tasks:**
1. Define model input format
   - Feature selection from bar data
   - Lookback window (how many bars to use)
   - Feature engineering (price changes, normalized values, etc.)

2. Define model output format
   - Binary classification (UP/DOWN) vs regression (price change)
   - Multi-horizon predictions (30s, 60s, 3min, 5min, 10min)
   - Confidence scores

3. Design model ensemble
   - XGBoost for gradient boosting
   - LightGBM for speed/efficiency
   - Voting or stacking strategy

**Deliverables:**
- `src/ml/model_config.py` - Model configuration
- `docs/ML_ARCHITECTURE.md` - Architecture documentation

---

### 2.2 Label Engineering

**Goal:** Create target labels for supervised learning

**Tasks:**
1. Implement forward-looking price movement calculation
   ```python
   # For each bar, calculate future price change
   future_price = close[t + horizon]
   current_price = close[t]
   change = (future_price - current_price) / current_price

   # Binary label
   label = 1 if change > threshold else 0
   ```

2. Multi-horizon labeling
   - 30 seconds → 0.5 minutes → look ahead 1 bar in 1m timeframe
   - 60 seconds → 1 minute → look ahead 1 bar in 1m timeframe
   - 3 minutes → look ahead 3 bars in 1m timeframe
   - 5 minutes → look ahead 1 bar in 5m timeframe
   - 10 minutes → look ahead 2 bars in 5m timeframe

3. Profit-based labeling (alternative)
   ```python
   # Label based on minimum profit threshold
   pip_value = 0.0001
   min_profit_pips = 3
   threshold = min_profit_pips * pip_value
   ```

**Deliverables:**
- `scripts/create_labels.py` - Label generation script
- `src/ml/label_engineering.py` - Label generation utilities

---

### 2.3 Training Pipeline

**Goal:** Train and validate ML models

**Tasks:**
1. Data preparation
   - Load bar data from database
   - Apply feature engineering
   - Add labels
   - Train/validation/test split (70/15/15)

2. Model training
   - XGBoost implementation
   - LightGBM implementation
   - Hyperparameter tuning
   - Cross-validation

3. Model evaluation
   - Accuracy, precision, recall, F1-score
   - Confusion matrix
   - ROC curve, AUC
   - Backtest simulation

4. Model persistence
   - Save trained models to disk
   - Version control (v1.0.0, v1.0.1, etc.)
   - Model metadata (training date, metrics, features)

**Deliverables:**
- `scripts/train_models.py` - Training script
- `src/ml/trainer.py` - Training utilities
- `src/ml/evaluator.py` - Evaluation utilities
- `models/` directory with saved models

---

### 2.4 Feature Selection

**Goal:** Optimize feature set for best performance

**Tasks:**
1. Correlation analysis
   - Identify highly correlated features
   - Remove redundant features

2. Feature importance
   - XGBoost feature importance
   - LightGBM feature importance
   - SHAP values for explainability

3. Dimensionality reduction (if needed)
   - PCA for feature compression
   - SelectKBest for top features

**Deliverables:**
- `scripts/feature_analysis.py` - Feature analysis script
- `docs/FEATURE_SELECTION_REPORT.md` - Analysis results

---

## Implementation Order

### Step 1: Label Engineering (Priority: HIGH)
Create the label generation system first, as it defines what the model will predict.

**Files to Create:**
- `src/ml/label_engineering.py`
- `scripts/create_labels.py`

**Estimated Time:** 1-2 hours

---

### Step 2: Data Preparation (Priority: HIGH)
Build dataset loading and preprocessing pipeline.

**Files to Create:**
- `src/ml/data_loader.py`
- `src/ml/feature_engineering.py`

**Estimated Time:** 2-3 hours

---

### Step 3: Model Training (Priority: HIGH)
Implement training pipeline for XGBoost and LightGBM.

**Files to Create:**
- `src/ml/trainer.py`
- `src/ml/models/xgboost_model.py`
- `src/ml/models/lightgbm_model.py`
- `scripts/train_models.py`

**Estimated Time:** 3-4 hours

---

### Step 4: Model Evaluation (Priority: MEDIUM)
Create evaluation and backtesting utilities.

**Files to Create:**
- `src/ml/evaluator.py`
- `src/ml/backtester.py`
- `scripts/evaluate_models.py`

**Estimated Time:** 2-3 hours

---

### Step 5: Feature Selection (Priority: LOW)
Optimize feature set based on initial training results.

**Files to Create:**
- `scripts/feature_analysis.py`

**Estimated Time:** 1-2 hours

---

## Success Criteria

Phase 2 is complete when:

| Criterion | Target | Status |
|-----------|--------|--------|
| Models trained | XGBoost + LightGBM | ⏳ Pending |
| Training accuracy | >60% | ⏳ Pending |
| Validation accuracy | >55% | ⏳ Pending |
| Model files saved | Yes | ⏳ Pending |
| Multi-horizon predictions | 5 horizons | ⏳ Pending |
| Backtest implemented | Yes | ⏳ Pending |
| Documentation complete | Yes | ⏳ Pending |

---

## Key Design Decisions

### 1. Prediction Target
**Recommendation:** Start with **binary classification** (price up/down)
- Simpler than regression
- Easier to evaluate
- Directly translates to trading signal (BUY/SELL)

### 2. Training Timeframe
**Recommendation:** Use **1m bars** for training
- Most granular data available
- 31+ bars per symbol = 155+ training samples
- Can aggregate to longer timeframes if needed

### 3. Lookback Window
**Recommendation:** Use **10-20 bars** lookback
- 10 bars = 10 minutes of history on 1m timeframe
- Captures recent price action
- Not too large to slow training

### 4. Feature Engineering
**Recommendation:** Add derived features
- Price changes: `(close - open) / open`
- Normalized indicators: `(rsi14 - 50) / 50`
- Trend features: `ema14 > ema50`
- Volatility ratios: `atr14 / close`

---

## Next Immediate Action

**Start with Label Engineering:**
1. Create `src/ml/label_engineering.py`
2. Implement forward-looking price movement calculation
3. Create labels for all 5 horizons
4. Test on existing bar data
5. Verify label distribution (avoid class imbalance)

Once labels are ready, proceed to Data Preparation.

---

**Plan Created:** 2025-10-14 10:09 UTC
**Phase 1 Status:** ✅ Complete (99.7% quality)
**Ready to Start Phase 2:** ✅ Yes

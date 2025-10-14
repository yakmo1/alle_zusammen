# -*- coding: utf-8 -*-
"""
Simple Model Training Script
Uses new ML pipeline: DataLoader → FeatureEngineer → Model Training
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from datetime import datetime
from src.utils.config_loader import get_config
from src.ml.data_loader import DataLoader
from src.ml.feature_engineering import FeatureEngineer
from src.ml.models.xgboost_model import XGBoostModel
from src.ml.models.lightgbm_model import LightGBMModel
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score


def train_model(
    symbols=None,
    timeframe='1m',
    horizon_label='label_h5',  # 3 minutes ahead
    algorithm='xgboost',
    lookback=5
):
    """
    Train a simple model

    Args:
        symbols: List of symbols (None = all from config)
        timeframe: Timeframe to use
        horizon_label: Label column to predict
        algorithm: 'xgboost' or 'lightgbm'
        lookback: Lookback window for features
    """
    print("="*70)
    print("SIMPLE MODEL TRAINING")
    print("="*70)
    print(f"Algorithm: {algorithm}")
    print(f"Timeframe: {timeframe}")
    print(f"Horizon: {horizon_label}")
    print(f"Lookback: {lookback}")
    print()

    # Get config
    config = get_config()
    if symbols is None:
        symbols = config.get_symbols()

    print(f"Symbols: {symbols}")
    print()

    # Load data
    print("Loading data...")
    loader = DataLoader(lookback_window=lookback, min_profit_pips=1.5)
    df = loader.load_training_data(symbols, timeframe=timeframe)

    if df is None or len(df) == 0:
        print("ERROR: No data loaded!")
        return None

    print(f"Loaded {len(df)} bars")
    print()

    # Feature engineering
    print("Engineering features...")
    engineer = FeatureEngineer()
    df = engineer.add_all_features(df)

    # Get feature columns
    feature_cols = engineer.get_feature_names(include_base=True)

    # Remove features that don't exist in data
    feature_cols = [col for col in feature_cols if col in df.columns]

    print(f"Features: {len(feature_cols)}")
    print(f"Features: {feature_cols[:10]}... (showing first 10)")
    print()

    # Create flat features
    print("Creating flat feature vectors...")
    X, y = loader.create_flat_features(df, feature_cols, horizon_label, lookback=lookback)

    if len(X) == 0:
        print("ERROR: No training samples created!")
        return None

    print(f"Training samples: {len(X)}")
    print(f"Feature dimensions: {X.shape}")
    print()

    # Check label distribution
    up_count = (y == 1).sum()
    down_count = (y == 0).sum()
    print(f"Label distribution: UP={up_count} ({up_count/len(y)*100:.1f}%), DOWN={down_count} ({down_count/len(y)*100:.1f}%)")
    print()

    # Split data
    print("Splitting data (70/15/15)...")
    X_train, X_val, X_test, y_train, y_val, y_test = \
        loader.train_val_test_split(X, y, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)

    print(f"Train: {len(X_train)} samples")
    print(f"Val:   {len(X_val)} samples")
    print(f"Test:  {len(X_test)} samples")
    print()

    # Train model
    print(f"Training {algorithm} model...")
    start_time = datetime.now()

    if algorithm == 'xgboost':
        model = XGBoostModel()
    else:
        model = LightGBMModel()

    model.train(X_train, y_train, X_val, y_val, verbose=False)

    duration = (datetime.now() - start_time).total_seconds()
    print(f"Training completed in {duration:.1f}s")
    print()

    # Evaluate
    print("Evaluating model...")

    # Predictions
    y_train_pred = model.predict(X_train)
    y_val_pred = model.predict(X_val)
    y_test_pred = model.predict(X_test)

    y_train_proba = model.predict_proba(X_train)[:, 1]
    y_val_proba = model.predict_proba(X_val)[:, 1]
    y_test_proba = model.predict_proba(X_test)[:, 1]

    # Metrics
    metrics = {
        'train_accuracy': accuracy_score(y_train, y_train_pred),
        'train_precision': precision_score(y_train, y_train_pred, zero_division=0),
        'train_recall': recall_score(y_train, y_train_pred, zero_division=0),
        'train_f1': f1_score(y_train, y_train_pred, zero_division=0),
        'train_auc': roc_auc_score(y_train, y_train_proba) if len(np.unique(y_train)) > 1 else 0,

        'val_accuracy': accuracy_score(y_val, y_val_pred),
        'val_precision': precision_score(y_val, y_val_pred, zero_division=0),
        'val_recall': recall_score(y_val, y_val_pred, zero_division=0),
        'val_f1': f1_score(y_val, y_val_pred, zero_division=0),
        'val_auc': roc_auc_score(y_val, y_val_proba) if len(np.unique(y_val)) > 1 else 0,

        'test_accuracy': accuracy_score(y_test, y_test_pred),
        'test_precision': precision_score(y_test, y_test_pred, zero_division=0),
        'test_recall': recall_score(y_test, y_test_pred, zero_division=0),
        'test_f1': f1_score(y_test, y_test_pred, zero_division=0),
        'test_auc': roc_auc_score(y_test, y_test_proba) if len(np.unique(y_test)) > 1 else 0,
    }

    # Print results
    print("="*70)
    print("RESULTS")
    print("="*70)
    print(f"{'Metric':<20} {'Train':<12} {'Val':<12} {'Test':<12}")
    print("-"*70)
    print(f"{'Accuracy':<20} {metrics['train_accuracy']:<12.4f} {metrics['val_accuracy']:<12.4f} {metrics['test_accuracy']:<12.4f}")
    print(f"{'Precision':<20} {metrics['train_precision']:<12.4f} {metrics['val_precision']:<12.4f} {metrics['test_precision']:<12.4f}")
    print(f"{'Recall':<20} {metrics['train_recall']:<12.4f} {metrics['val_recall']:<12.4f} {metrics['test_recall']:<12.4f}")
    print(f"{'F1-Score':<20} {metrics['train_f1']:<12.4f} {metrics['val_f1']:<12.4f} {metrics['test_f1']:<12.4f}")
    print(f"{'ROC-AUC':<20} {metrics['train_auc']:<12.4f} {metrics['val_auc']:<12.4f} {metrics['test_auc']:<12.4f}")
    print("="*70)

    # Save model
    models_dir = Path('models')
    models_dir.mkdir(exist_ok=True)

    model_filename = f"{algorithm}_{timeframe}_{horizon_label}_lookback{lookback}.model"
    model_path = models_dir / model_filename

    print(f"\nSaving model to {model_path}...")
    model.save(str(model_path))
    print("Model saved!")

    return {
        'model': model,
        'metrics': metrics,
        'model_path': model_path,
        'feature_cols': feature_cols,
        'lookback': lookback
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Train ML Model')
    parser.add_argument('--algorithm', type=str, default='xgboost', choices=['xgboost', 'lightgbm'])
    parser.add_argument('--timeframe', type=str, default='1m')
    parser.add_argument('--horizon', type=str, default='label_h5', help='Label column (label_h1, label_h3, label_h5, label_h10)')
    parser.add_argument('--lookback', type=int, default=5, help='Lookback window')

    args = parser.parse_args()

    result = train_model(
        algorithm=args.algorithm,
        timeframe=args.timeframe,
        horizon_label=args.horizon,
        lookback=args.lookback
    )

    if result:
        print("\nTraining successful!")
    else:
        print("\nTraining failed!")
        sys.exit(1)

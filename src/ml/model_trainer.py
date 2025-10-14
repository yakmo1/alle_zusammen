"""
ML Model Trainer
Multi-Horizon Forecasting mit XGBoost und LightGBM
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import joblib
import os
from pathlib import Path

from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import lightgbm as lgb

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config
from ..data.database_manager import get_database


class ModelTrainer:
    """Trainiert und evaluiert ML-Models für Trading"""

    def __init__(self, db_type: str = 'local'):
        """
        Initialisiert den Model Trainer

        Args:
            db_type: Database Type
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)

        # Model Configuration
        self.horizons = [30, 60, 180, 300, 600]  # Sekunden: 30s, 1m, 3m, 5m, 10m
        self.algorithms = ['xgboost', 'lightgbm']
        self.timeframes = ['1m', '5m', '15m']

        # Paths
        self.models_dir = Path('models')
        self.models_dir.mkdir(exist_ok=True)

        # Feature columns (werden automatisch erkannt)
        self.feature_columns = []

    def fetch_training_data(
        self,
        symbol: str,
        timeframe: str,
        days: int = 30
    ) -> Optional[pd.DataFrame]:
        """
        Holt Trainingsdaten aus Database

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            days: Anzahl Tage zurück

        Returns:
            DataFrame mit Features und Targets
        """
        try:
            # Fetch features with bars
            query = """
                SELECT
                    f.timestamp,
                    f.symbol,
                    b.open, b.high, b.low, b.close, b.volume,
                    f.sma_10, f.sma_20, f.sma_50,
                    f.ema_10, f.ema_20,
                    f.rsi_14,
                    f.macd, f.macd_signal, f.macd_hist,
                    f.bb_upper, f.bb_middle, f.bb_lower,
                    f.atr_14
                FROM features f
                JOIN bars_{timeframe} b ON f.symbol = b.symbol
                    AND f.timestamp = b.timestamp
                WHERE f.symbol = %s
                  AND f.timeframe = %s
                  AND f.timestamp >= NOW() - INTERVAL '{days} days'
                ORDER BY f.timestamp ASC
            """.format(timeframe=timeframe, days=days)

            results = self.db.fetch_all_dict(query, (symbol, timeframe))

            if not results or len(results) < 100:
                self.logger.warning(f"Not enough data for {symbol} {timeframe}: {len(results) if results else 0} rows")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(results)

            # Create target variables for different horizons
            for horizon in self.horizons:
                # Future price (in N seconds/bars)
                bars_ahead = max(1, horizon // 60) if timeframe == '1m' else 1
                df[f'target_{horizon}s'] = df['close'].shift(-bars_ahead)

                # Price direction (up=1, down=0)
                df[f'direction_{horizon}s'] = (df[f'target_{horizon}s'] > df['close']).astype(int)

            # Drop rows with NaN
            df = df.dropna()

            self.logger.info(f"Fetched {len(df)} training samples for {symbol} {timeframe}")
            return df

        except Exception as e:
            log_exception(self.logger, e, f"Failed to fetch training data for {symbol} {timeframe}")
            return None

    def prepare_features(self, df: pd.DataFrame) -> Tuple[List[str], pd.DataFrame]:
        """
        Bereitet Features vor

        Args:
            df: Input DataFrame

        Returns:
            (Feature columns, DataFrame)
        """
        # Select feature columns (exclude metadata and targets)
        exclude_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        target_cols = [col for col in df.columns if col.startswith(('target_', 'direction_'))]

        feature_cols = [col for col in df.columns
                       if col not in exclude_cols + target_cols]

        # Add price-based features
        df['price_change_1'] = df['close'].pct_change(1)
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_10'] = df['close'].pct_change(10)

        feature_cols.extend(['price_change_1', 'price_change_5', 'price_change_10'])

        # Drop NaN again
        df = df.dropna()

        return feature_cols, df

    def train_model(
        self,
        symbol: str,
        timeframe: str,
        horizon: int,
        algorithm: str = 'xgboost'
    ) -> Optional[Dict[str, Any]]:
        """
        Trainiert ein Model

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            horizon: Prediction Horizon (Sekunden)
            algorithm: Algorithm ('xgboost' oder 'lightgbm')

        Returns:
            Model Info Dictionary
        """
        try:
            self.logger.info(f"Training {algorithm} model for {symbol} {timeframe} {horizon}s horizon...")

            # Fetch training data
            df = self.fetch_training_data(symbol, timeframe, days=30)
            if df is None or len(df) < 100:
                return None

            # Prepare features
            feature_cols, df = self.prepare_features(df)
            self.feature_columns = feature_cols

            # Target column
            target_col = f'target_{horizon}s'
            if target_col not in df.columns:
                self.logger.error(f"Target column {target_col} not found")
                return None

            # Split data (time-series split)
            X = df[feature_cols].values
            y = df[target_col].values

            # Train/test split (80/20, time-based)
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            if algorithm == 'xgboost':
                model = xgb.XGBRegressor(
                    n_estimators=200,
                    learning_rate=0.05,
                    max_depth=6,
                    min_child_weight=2,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    gamma=0.1,
                    random_state=42,
                    n_jobs=-1
                )
            else:  # lightgbm
                model = lgb.LGBMRegressor(
                    n_estimators=200,
                    learning_rate=0.05,
                    max_depth=6,
                    num_leaves=31,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    n_jobs=-1,
                    verbose=-1
                )

            model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred_train = model.predict(X_train_scaled)
            y_pred_test = model.predict(X_test_scaled)

            metrics = {
                'train_mae': float(mean_absolute_error(y_train, y_pred_train)),
                'train_rmse': float(np.sqrt(mean_squared_error(y_train, y_pred_train))),
                'train_r2': float(r2_score(y_train, y_pred_train)),
                'test_mae': float(mean_absolute_error(y_test, y_pred_test)),
                'test_rmse': float(np.sqrt(mean_squared_error(y_test, y_pred_test))),
                'test_r2': float(r2_score(y_test, y_pred_test)),
                'samples_train': len(X_train),
                'samples_test': len(X_test)
            }

            self.logger.info(f"Model trained: R2={metrics['test_r2']:.4f}, RMSE={metrics['test_rmse']:.6f}")

            # Save model
            model_info = {
                'model': model,
                'scaler': scaler,
                'feature_columns': feature_cols,
                'symbol': symbol,
                'timeframe': timeframe,
                'horizon': horizon,
                'algorithm': algorithm,
                'metrics': metrics,
                'trained_at': datetime.now().isoformat(),
                'version': 'v1.0'
            }

            # Save to disk
            model_path = self._get_model_path(symbol, timeframe, horizon, algorithm)
            joblib.dump(model_info, model_path)
            self.logger.info(f"Model saved to {model_path}")

            # Save to database
            self._save_model_to_db(model_info)

            return model_info

        except Exception as e:
            log_exception(self.logger, e, f"Failed to train model for {symbol} {timeframe} {horizon}s")
            return None

    def train_all_models(
        self,
        symbols: List[str] = None,
        timeframes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Trainiert alle Models

        Args:
            symbols: Liste der Symbols (None = aus Config)
            timeframes: Liste der Timeframes (None = default)

        Returns:
            Training Results
        """
        symbols = symbols or self.config.get_symbols()
        timeframes = timeframes or self.timeframes

        results = {
            'successful': [],
            'failed': [],
            'total': 0,
            'start_time': datetime.now()
        }

        total = len(symbols) * len(timeframes) * len(self.horizons) * len(self.algorithms)
        current = 0

        for symbol in symbols:
            for timeframe in timeframes:
                for horizon in self.horizons:
                    for algorithm in self.algorithms:
                        current += 1
                        self.logger.info(f"Training model {current}/{total}: {symbol} {timeframe} {horizon}s {algorithm}")

                        model_info = self.train_model(symbol, timeframe, horizon, algorithm)

                        if model_info:
                            results['successful'].append({
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'horizon': horizon,
                                'algorithm': algorithm,
                                'metrics': model_info['metrics']
                            })
                        else:
                            results['failed'].append({
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'horizon': horizon,
                                'algorithm': algorithm
                            })

        results['total'] = total
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()

        self.logger.info(f"Training complete: {len(results['successful'])}/{total} successful")

        return results

    def _get_model_path(
        self,
        symbol: str,
        timeframe: str,
        horizon: int,
        algorithm: str
    ) -> Path:
        """Generiert Model Path"""
        filename = f"{symbol}_{timeframe}_{horizon}s_{algorithm}.joblib"
        return self.models_dir / filename

    def _save_model_to_db(self, model_info: Dict[str, Any]):
        """Speichert Model Info in Database"""
        try:
            insert_sql = """
                INSERT INTO model_versions
                    (model_name, version, algorithm, symbol, timeframe,
                     prediction_horizon, metrics, is_active, created_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (model_name, version)
                DO UPDATE SET
                    metrics = EXCLUDED.metrics,
                    is_active = EXCLUDED.is_active,
                    created_at = EXCLUDED.created_at
            """

            model_name = f"{model_info['symbol']}_{model_info['timeframe']}_{model_info['horizon']}s"

            import json
            self.db.execute(insert_sql, (
                model_name,
                model_info['version'],
                model_info['algorithm'],
                model_info['symbol'],
                model_info['timeframe'],
                model_info['horizon'],
                json.dumps(model_info['metrics']),
                True,  # is_active
                datetime.now()
            ))

            self.logger.info(f"Model info saved to database: {model_name}")

        except Exception as e:
            log_exception(self.logger, e, "Failed to save model info to database")

    def load_model(
        self,
        symbol: str,
        timeframe: str,
        horizon: int,
        algorithm: str = 'xgboost'
    ) -> Optional[Dict[str, Any]]:
        """
        Lädt ein gespeichertes Model

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            horizon: Prediction Horizon
            algorithm: Algorithm

        Returns:
            Model Info Dictionary
        """
        try:
            model_path = self._get_model_path(symbol, timeframe, horizon, algorithm)

            if not model_path.exists():
                self.logger.warning(f"Model not found: {model_path}")
                return None

            model_info = joblib.load(model_path)
            self.logger.info(f"Model loaded from {model_path}")

            return model_info

        except Exception as e:
            log_exception(self.logger, e, f"Failed to load model from {model_path}")
            return None


if __name__ == "__main__":
    # Test
    print("=== Model Trainer Test ===\n")

    trainer = ModelTrainer()

    # Train single model
    print("Training single model...")
    model_info = trainer.train_model('EURUSD', '1m', 60, 'xgboost')

    if model_info:
        print("\nModel Metrics:")
        for key, value in model_info['metrics'].items():
            print(f"  {key}: {value:.6f}")

        # Test loading
        print("\nTesting model loading...")
        loaded_model = trainer.load_model('EURUSD', '1m', 60, 'xgboost')
        if loaded_model:
            print("✓ Model loaded successfully")

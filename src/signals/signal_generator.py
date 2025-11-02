"""
Signal Generator - Phase 3
Generates trading signals using trained ML models
"""

import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

from src.utils.logger import get_logger
from src.data.database_manager import get_database
from src.ml.feature_engineering import FeatureEngineer

logger = get_logger('SignalGenerator')


class SignalGenerator:
    """Generates trading signals from ML model predictions"""

    def __init__(self,
                 model_dir: str = 'models',
                 confidence_threshold: float = 0.70,
                 max_signals_per_hour: int = 10):
        """
        Initialize Signal Generator

        Args:
            model_dir: Directory containing trained models
            confidence_threshold: Minimum confidence for signal (0-1)
            max_signals_per_hour: Rate limit for signal generation
        """
        self.model_dir = Path(model_dir)
        self.confidence_threshold = confidence_threshold
        self.max_signals_per_hour = max_signals_per_hour
        self.db = get_database('local')
        self.feature_engineer = FeatureEngineer()

        # Load models and metadata
        self.models = {}
        self.model_metadata = {}
        self._load_models()

        # Track signal rate limiting
        self.recent_signals = []

        logger.info(f"Signal Generator initialized with {len(self.models)} models")
        logger.info(f"Confidence threshold: {confidence_threshold}")

    def _load_models(self):
        """Load all trained models from model directory"""
        if not self.model_dir.exists():
            logger.warning(f"Model directory not found: {self.model_dir}")
            return

        # Support both .pkl and .model extensions
        model_files = list(self.model_dir.glob('*.model')) + list(self.model_dir.glob('*_model.pkl'))

        for model_file in model_files:
            try:
                # Load model
                model = joblib.load(model_file)

                # Load metadata (.meta or _metadata.json)
                metadata = {}
                metadata_file = model_file.with_suffix('.meta')

                if metadata_file.exists():
                    try:
                        # Try loading as pickle first
                        metadata = joblib.load(metadata_file)
                    except:
                        # Try as JSON
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                        except:
                            logger.warning(f"Could not load metadata from {metadata_file}")
                else:
                    # Try _metadata.json format
                    metadata_file = model_file.with_name(model_file.stem + '_metadata.json')
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                        except:
                            logger.warning(f"Could not load metadata from {metadata_file}")

                model_name = model_file.stem.replace('_model', '').replace('.model', '')
                self.models[model_name] = model
                self.model_metadata[model_name] = metadata

                logger.info(f"Loaded model: {model_name}")
                if metadata:
                    logger.info(f"  Test Accuracy: {metadata.get('test_accuracy', 'N/A')}")
                    logger.info(f"  Algorithm: {metadata.get('algorithm', 'N/A')}")

            except Exception as e:
                logger.error(f"Error loading model {model_file}: {e}")

    def get_latest_features(self, symbol: str, timeframe: str = '1m', lookback: int = 5) -> Optional[pd.DataFrame]:
        """
        Fetch latest bars and features from database

        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            timeframe: Bar timeframe
            lookback: Number of recent bars to fetch

        Returns:
            DataFrame with features or None if insufficient data
        """
        try:
            bar_table = f"bars_{symbol.lower()}"

            sql = f"""
                SELECT
                    timestamp, open, high, low, close, volume, tick_count,
                    rsi14, macd_main, bb_upper, bb_lower, atr14
                FROM {bar_table}
                WHERE timeframe = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """

            result = self.db.fetch_all(sql, (timeframe, lookback + 1))

            if not result or len(result) < lookback + 1:
                logger.debug(f"Insufficient data for {symbol}: {len(result) if result else 0} bars")
                return None

            # Convert to DataFrame (reverse to chronological order)
            df = pd.DataFrame(result[::-1], columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'tick_count',
                'rsi14', 'macd_main', 'bb_upper', 'bb_lower', 'atr14'
            ])

            # Add derived features
            df = self.feature_engineer.add_price_features(df)
            df = self.feature_engineer.add_return_features(df)
            df = self.feature_engineer.add_normalized_features(df)

            return df

        except Exception as e:
            logger.error(f"Error fetching features for {symbol}: {e}")
            return None

    def prepare_features_for_inference(self, df: pd.DataFrame, lookback: int = 5) -> np.ndarray:
        """
        Prepare features in the same format as training

        Args:
            df: DataFrame with features
            lookback: Lookback window

        Returns:
            Flattened feature array
        """
        # Feature columns (must match training)
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume',
            'rsi14', 'macd_main', 'bb_upper', 'bb_lower', 'atr14',
            'price_change', 'high_low_range', 'body_size',
            'upper_shadow', 'lower_shadow', 'close_position',
            'return_1', 'return_2', 'return_3', 'return_5',
            'rsi_norm', 'macd_norm', 'bb_position',
            'atr_norm', 'volatility_10'
        ]

        # Check if we have all required columns
        missing_cols = [col for col in feature_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"Missing feature columns: {missing_cols}")
            # Fill missing columns with 0
            for col in missing_cols:
                df[col] = 0.0

        # Extract features for last `lookback` bars (including current)
        flat_features = []

        # We need lookback+1 bars to create features with lookback
        if len(df) < lookback + 1:
            logger.error(f"Not enough bars: {len(df)} < {lookback + 1}")
            return None

        # Take last lookback+1 rows
        recent_df = df.iloc[-(lookback + 1):]

        # Flatten features: [bar_t-5, bar_t-4, ..., bar_t-1, bar_t]
        for i in range(lookback + 1):
            row_features = recent_df.iloc[i][feature_cols].values
            flat_features.extend(row_features)

        return np.array([flat_features])  # Shape: (1, n_features)

    def make_prediction(self, symbol: str, model_name: Optional[str] = None) -> Optional[Dict]:
        """
        Make prediction for a symbol

        Args:
            symbol: Trading symbol
            model_name: Specific model to use (or None for best model)

        Returns:
            Prediction dict with signal, confidence, features
        """
        if not self.models:
            logger.error("No models loaded")
            return None

        # Use best model if not specified
        if model_name is None:
            # Select model with highest test accuracy
            best_model = max(
                self.model_metadata.items(),
                key=lambda x: x[1].get('test_accuracy', 0)
            )[0] if self.model_metadata else list(self.models.keys())[0]
            model_name = best_model

        if model_name not in self.models:
            logger.error(f"Model not found: {model_name}")
            return None

        model = self.models[model_name]

        # Get latest features
        df = self.get_latest_features(symbol)
        if df is None:
            return None

        # Prepare features for inference
        X = self.prepare_features_for_inference(df)
        if X is None:
            return None

        try:
            # Make prediction
            prediction_proba = model.predict_proba(X)[0]
            prediction_class = model.predict(X)[0]

            # prediction_proba: [prob_down, prob_up]
            # prediction_class: 0=DOWN, 1=UP

            prob_down = prediction_proba[0]
            prob_up = prediction_proba[1]

            # Determine signal and confidence
            if prob_up > self.confidence_threshold:
                signal = 'BUY'
                confidence = prob_up
            elif prob_down > self.confidence_threshold:
                signal = 'SELL'
                confidence = prob_down
            else:
                signal = 'FLAT'
                confidence = max(prob_up, prob_down)

            return {
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'prob_up': prob_up,
                'prob_down': prob_down,
                'model': model_name,
                'timestamp': datetime.now(),
                'last_close': float(df.iloc[-1]['close']),
                'features': X[0].tolist()
            }

        except Exception as e:
            logger.error(f"Error making prediction for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def check_rate_limit(self) -> bool:
        """
        Check if we're within signal generation rate limit

        Returns:
            True if we can generate more signals
        """
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)

        # Remove old signals
        self.recent_signals = [
            ts for ts in self.recent_signals
            if ts > hour_ago
        ]

        # Check limit
        if len(self.recent_signals) >= self.max_signals_per_hour:
            logger.debug(f"Rate limit reached: {len(self.recent_signals)}/{self.max_signals_per_hour}")
            return False

        return True

    def save_signal(self, prediction: Dict, paper_trading: bool = False):
        """
        Save signal to database

        Args:
            prediction: Prediction dict from make_prediction
            paper_trading: If True, mark as paper trading signal
        """
        try:
            # Create signals table if not exists
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS signals (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    signal VARCHAR(10) NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL,
                    prob_up DOUBLE PRECISION,
                    prob_down DOUBLE PRECISION,
                    model_name VARCHAR(50),
                    price_at_signal DOUBLE PRECISION,
                    paper_trading BOOLEAN DEFAULT FALSE,
                    executed BOOLEAN DEFAULT FALSE,
                    executed_at TIMESTAMP WITH TIME ZONE,
                    order_ticket BIGINT,
                    metadata JSONB
                );

                CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals (timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals (symbol);
                CREATE INDEX IF NOT EXISTS idx_signals_executed ON signals (executed) WHERE NOT executed;
            """
            self.db.execute(create_table_sql)

            # Insert signal
            insert_sql = """
                INSERT INTO signals
                (timestamp, symbol, signal, confidence, prob_up, prob_down,
                 model_name, price_at_signal, paper_trading, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """

            metadata = {
                'features_shape': len(prediction['features']),
                'threshold': self.confidence_threshold
            }

            values = (
                prediction['timestamp'],
                prediction['symbol'],
                prediction['signal'],
                prediction['confidence'],
                prediction['prob_up'],
                prediction['prob_down'],
                prediction['model'],
                prediction['last_close'],
                paper_trading,
                json.dumps(metadata)
            )

            result = self.db.fetch_one(insert_sql, values)
            signal_id = result[0] if result else None

            logger.info(
                f"Signal saved: {prediction['symbol']} {prediction['signal']} "
                f"(confidence: {prediction['confidence']:.2%}, id: {signal_id})"
            )

            # Track for rate limiting
            self.recent_signals.append(prediction['timestamp'])

            return signal_id

        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_signals(self, symbols: List[str], paper_trading: bool = False) -> List[Dict]:
        """
        Generate signals for multiple symbols

        Args:
            symbols: List of symbols to generate signals for
            paper_trading: If True, mark signals as paper trading

        Returns:
            List of generated signals
        """
        signals = []

        # Check rate limit
        if not self.check_rate_limit():
            logger.warning("Rate limit reached, skipping signal generation")
            return signals

        for symbol in symbols:
            try:
                prediction = self.make_prediction(symbol)

                if prediction is None:
                    continue

                # Only save non-FLAT signals or if in paper trading mode
                if prediction['signal'] != 'FLAT' or paper_trading:
                    signal_id = self.save_signal(prediction, paper_trading)
                    if signal_id:
                        prediction['id'] = signal_id
                        signals.append(prediction)

            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {e}")

        return signals

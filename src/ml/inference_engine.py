"""
ML Inference Engine
Real-time Predictions mit trainierten Models
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import time
from collections import defaultdict

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config
from ..data.database_manager import get_database
from .model_trainer import ModelTrainer


class InferenceEngine:
    """Führt Real-time ML Predictions aus"""

    def __init__(self, db_type: str = 'local'):
        """
        Initialisiert die Inference Engine

        Args:
            db_type: Database Type
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)
        self.model_trainer = ModelTrainer(db_type)

        # Loaded models cache
        self.models = {}  # key: (symbol, timeframe, horizon, algorithm)

        # Configuration
        self.symbols = self.config.get_symbols()
        self.timeframes = ['1m', '5m', '15m']
        self.horizons = [30, 60, 180, 300, 600]  # Sekunden
        self.default_algorithm = 'xgboost'

        # State
        self.is_running = False
        self.inference_thread = None

        # Statistics
        self.stats = {
            'predictions_made': defaultdict(int),
            'errors': 0,
            'start_time': None
        }

        # Prediction interval
        self.prediction_interval = 10  # Sekunden

    def load_models(self, symbols: List[str] = None, timeframes: List[str] = None):
        """
        Lädt alle benötigten Models

        Args:
            symbols: Liste der Symbols
            timeframes: Liste der Timeframes
        """
        symbols = symbols or self.symbols
        timeframes = timeframes or self.timeframes

        self.logger.info("Loading models...")

        loaded = 0
        failed = 0

        for symbol in symbols:
            for timeframe in timeframes:
                for horizon in self.horizons:
                    # Try xgboost first, dann lightgbm
                    for algorithm in ['xgboost', 'lightgbm']:
                        model_info = self.model_trainer.load_model(
                            symbol, timeframe, horizon, algorithm
                        )

                        if model_info:
                            key = (symbol, timeframe, horizon, algorithm)
                            self.models[key] = model_info
                            loaded += 1
                            break  # Nur ein Algorithm pro Kombination

                        failed += 1

        self.logger.info(f"Models loaded: {loaded} successful, {failed} failed")

    def get_latest_features(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[pd.DataFrame]:
        """
        Holt neueste Features für Prediction

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe

        Returns:
            DataFrame mit Features
        """
        try:
            query = """
                SELECT
                    f.timestamp,
                    b.close,
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
                ORDER BY f.timestamp DESC
                LIMIT 20
            """.format(timeframe=timeframe)

            results = self.db.fetch_all_dict(query, (symbol, timeframe))

            if not results:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(results)
            df = df.sort_values('timestamp')

            # Calculate price changes
            df['price_change_1'] = df['close'].pct_change(1)
            df['price_change_5'] = df['close'].pct_change(5)
            df['price_change_10'] = df['close'].pct_change(10)

            # Drop NaN
            df = df.dropna()

            return df

        except Exception as e:
            log_exception(self.logger, e, f"Failed to get latest features for {symbol} {timeframe}")
            return None

    def predict(
        self,
        symbol: str,
        timeframe: str,
        horizon: int,
        algorithm: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Macht eine Prediction

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            horizon: Prediction Horizon (Sekunden)
            algorithm: Algorithm (None = default)

        Returns:
            Prediction Dictionary
        """
        try:
            algorithm = algorithm or self.default_algorithm

            # Get model
            key = (symbol, timeframe, horizon, algorithm)
            if key not in self.models:
                self.logger.warning(f"Model not found: {key}")
                return None

            model_info = self.models[key]
            model = model_info['model']
            scaler = model_info['scaler']
            feature_columns = model_info['feature_columns']

            # Get latest features
            df = self.get_latest_features(symbol, timeframe)
            if df is None or len(df) == 0:
                return None

            # Get latest row
            latest = df.iloc[-1]

            # Prepare features
            X = []
            for col in feature_columns:
                if col in latest:
                    X.append(float(latest[col]))
                else:
                    X.append(0.0)

            X = np.array(X).reshape(1, -1)

            # Scale
            X_scaled = scaler.transform(X)

            # Predict
            predicted_price = float(model.predict(X_scaled)[0])
            current_price = float(latest['close'])

            # Calculate confidence (based on historical model performance)
            r2_score = model_info['metrics'].get('test_r2', 0.0)
            confidence = max(0.0, min(1.0, r2_score))  # 0-1 range

            # Determine signal
            price_change = (predicted_price - current_price) / current_price
            if abs(price_change) < 0.0001:  # < 0.01%
                signal = 'HOLD'
            elif price_change > 0:
                signal = 'BUY'
            else:
                signal = 'SELL'

            # Create prediction
            prediction = {
                'symbol': symbol,
                'timeframe': timeframe,
                'horizon': horizon,
                'algorithm': algorithm,
                'timestamp': datetime.now(),
                'current_price': current_price,
                'predicted_price': predicted_price,
                'price_change_pct': price_change * 100,
                'signal': signal,
                'confidence': confidence,
                'model_version': model_info['version'],
                'features_timestamp': latest['timestamp']
            }

            # Save to database
            self._save_prediction(prediction)

            self.stats['predictions_made'][f"{symbol}_{timeframe}_{horizon}s"] += 1

            return prediction

        except Exception as e:
            log_exception(self.logger, e, f"Prediction failed for {symbol} {timeframe} {horizon}s")
            self.stats['errors'] += 1
            return None

    def predict_all_horizons(
        self,
        symbol: str,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """
        Macht Predictions für alle Horizons

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe

        Returns:
            Liste von Predictions
        """
        predictions = []

        for horizon in self.horizons:
            prediction = self.predict(symbol, timeframe, horizon)
            if prediction:
                predictions.append(prediction)

        return predictions

    def _save_prediction(self, prediction: Dict[str, Any]):
        """
        Speichert Prediction in Database

        Args:
            prediction: Prediction Dictionary
        """
        try:
            insert_sql = """
                INSERT INTO model_forecasts
                    (timestamp, symbol, timeframe, prediction_horizon,
                     current_price, predicted_price, signal, confidence,
                     algorithm, model_version)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            self.db.execute(insert_sql, (
                prediction['timestamp'],
                prediction['symbol'],
                prediction['timeframe'],
                prediction['horizon'],
                prediction['current_price'],
                prediction['predicted_price'],
                prediction['signal'],
                prediction['confidence'],
                prediction['algorithm'],
                prediction['model_version']
            ))

        except Exception as e:
            log_exception(self.logger, e, "Failed to save prediction to database")

    def _inference_loop(self):
        """Inference Loop (läuft in eigenem Thread)"""
        self.logger.info("Inference engine started")

        while self.is_running:
            try:
                # Make predictions for all symbols and timeframes
                for symbol in self.symbols:
                    for timeframe in self.timeframes:
                        predictions = self.predict_all_horizons(symbol, timeframe)

                        if predictions:
                            self.logger.info(
                                f"Made {len(predictions)} predictions for {symbol} {timeframe}"
                            )

                # Sleep
                time.sleep(self.prediction_interval)

            except Exception as e:
                log_exception(self.logger, e, "Error in inference loop")
                time.sleep(5)

        self.logger.info("Inference engine stopped")

    def start(self):
        """Startet die Inference Engine"""
        if self.is_running:
            self.logger.warning("Inference engine already running")
            return

        self.logger.info("Starting inference engine...")

        # Load models
        self.load_models()

        if not self.models:
            self.logger.error("No models loaded, cannot start inference engine")
            return

        self.is_running = True
        self.stats['start_time'] = datetime.now()

        # Start thread
        self.inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self.inference_thread.start()

        self.logger.info(f"✓ Inference engine started with {len(self.models)} models")

    def stop(self):
        """Stoppt die Inference Engine"""
        if not self.is_running:
            return

        self.logger.info("Stopping inference engine...")

        self.is_running = False

        # Wait for thread
        if self.inference_thread:
            self.inference_thread.join(timeout=10)

        # Log statistics
        self._log_statistics()

        self.logger.info("✓ Inference engine stopped")

    def _log_statistics(self):
        """Loggt Statistiken"""
        if self.stats['start_time']:
            runtime = (datetime.now() - self.stats['start_time']).total_seconds()

            self.logger.info("=== Inference Engine Statistics ===")
            self.logger.info(f"Runtime: {runtime:.0f}s")
            self.logger.info("Predictions Made:")
            for key, count in self.stats['predictions_made'].items():
                self.logger.info(f"  {key}: {count}")
            self.logger.info(f"Errors: {self.stats['errors']}")

    def get_latest_predictions(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Holt neueste Predictions

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            limit: Anzahl Predictions

        Returns:
            Liste von Predictions
        """
        query = """
            SELECT
                timestamp, symbol, timeframe, prediction_horizon,
                current_price, predicted_price, signal, confidence,
                algorithm, model_version
            FROM model_forecasts
            WHERE symbol = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """

        return self.db.fetch_all_dict(query, (symbol, timeframe, limit))

    def __enter__(self):
        """Context Manager Enter"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Exit"""
        self.stop()


if __name__ == "__main__":
    # Test
    print("=== Inference Engine Test ===\n")

    try:
        engine = InferenceEngine()

        # Load models
        print("Loading models...")
        engine.load_models(symbols=['EURUSD'], timeframes=['1m'])
        print(f"Loaded {len(engine.models)} models\n")

        if engine.models:
            # Make single prediction
            print("Making prediction...")
            prediction = engine.predict('EURUSD', '1m', 60)

            if prediction:
                print("\nPrediction:")
                print(f"  Current Price: {prediction['current_price']:.5f}")
                print(f"  Predicted Price: {prediction['predicted_price']:.5f}")
                print(f"  Change: {prediction['price_change_pct']:.3f}%")
                print(f"  Signal: {prediction['signal']}")
                print(f"  Confidence: {prediction['confidence']:.3f}")
            else:
                print("No prediction made (insufficient data)")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

"""
Feature Calculator
Berechnet Technical Indicators aus Bar-Daten
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import threading
import time

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config
from .database_manager import get_database


class FeatureCalculator:
    """Berechnet Technical Indicators für Trading"""

    def __init__(self, symbols: List[str] = None, timeframes: List[str] = None, db_type: str = 'local'):
        """
        Initialisiert den Feature Calculator

        Args:
            symbols: Liste der Symbols
            timeframes: Liste der Timeframes
            db_type: Database Type
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)

        # Configuration
        self.symbols = symbols or self.config.get_symbols()
        self.timeframes = timeframes or ['1m', '5m', '15m', '1h']

        # State
        self.is_running = False
        self.calculator_thread = None

        # Statistics
        self.stats = {
            'features_calculated': 0,
            'errors': 0,
            'start_time': None
        }

    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period, min_periods=period).mean()

    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Moving Average Convergence Divergence"""
        ema_fast = self.calculate_ema(data, fast)
        ema_slow = self.calculate_ema(data, slow)

        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def calculate_bollinger_bands(self, data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """Bollinger Bands"""
        sma = self.calculate_sma(data, period)
        std = data.rolling(window=period).std()

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return {
            'upper': upper,
            'middle': sma,
            'lower': lower
        }

    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        atr = true_range.rolling(window=period).mean()
        return atr

    def fetch_bars(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """
        Holt Bar-Daten aus Database

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            limit: Anzahl Bars

        Returns:
            DataFrame mit Bar-Daten oder None
        """
        table_name = f"bars_{timeframe}"

        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM {table_name}
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """

        try:
            results = self.db.fetch_all_dict(query, (symbol, limit))

            if not results:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(results)
            df = df.sort_values('timestamp')
            df.set_index('timestamp', inplace=True)

            # Convert to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            return df

        except Exception as e:
            log_exception(self.logger, e, f"Failed to fetch bars for {symbol} {timeframe}")
            return None

    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet alle Features für DataFrame

        Args:
            df: DataFrame mit OHLCV Daten

        Returns:
            DataFrame mit Features
        """
        if df is None or len(df) < 50:
            return None

        try:
            features = df.copy()

            # Moving Averages
            features['sma_10'] = self.calculate_sma(df['close'], 10)
            features['sma_20'] = self.calculate_sma(df['close'], 20)
            features['sma_50'] = self.calculate_sma(df['close'], 50)

            features['ema_10'] = self.calculate_ema(df['close'], 10)
            features['ema_20'] = self.calculate_ema(df['close'], 20)

            # RSI
            features['rsi_14'] = self.calculate_rsi(df['close'], 14)

            # MACD
            macd = self.calculate_macd(df['close'])
            features['macd'] = macd['macd']
            features['macd_signal'] = macd['signal']
            features['macd_hist'] = macd['histogram']

            # Bollinger Bands
            bb = self.calculate_bollinger_bands(df['close'])
            features['bb_upper'] = bb['upper']
            features['bb_middle'] = bb['middle']
            features['bb_lower'] = bb['lower']

            # ATR
            features['atr_14'] = self.calculate_atr(df['high'], df['low'], df['close'])

            # Drop NaN
            features = features.dropna()

            return features

        except Exception as e:
            log_exception(self.logger, e, "Failed to calculate features")
            return None

    def save_features(self, symbol: str, timeframe: str, features: pd.DataFrame):
        """
        Speichert Features in Database

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            features: DataFrame mit Features
        """
        if features is None or len(features) == 0:
            return

        insert_sql = """
            INSERT INTO features
                (symbol, timestamp, timeframe, sma_10, sma_20, sma_50,
                 ema_10, ema_20, rsi_14, macd, macd_signal, macd_hist,
                 bb_upper, bb_middle, bb_lower, atr_14)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timestamp, timeframe)
            DO UPDATE SET
                sma_10 = EXCLUDED.sma_10,
                sma_20 = EXCLUDED.sma_20,
                sma_50 = EXCLUDED.sma_50,
                ema_10 = EXCLUDED.ema_10,
                ema_20 = EXCLUDED.ema_20,
                rsi_14 = EXCLUDED.rsi_14,
                macd = EXCLUDED.macd,
                macd_signal = EXCLUDED.macd_signal,
                macd_hist = EXCLUDED.macd_hist,
                bb_upper = EXCLUDED.bb_upper,
                bb_middle = EXCLUDED.bb_middle,
                bb_lower = EXCLUDED.bb_lower,
                atr_14 = EXCLUDED.atr_14,
                created_at = CURRENT_TIMESTAMP
        """

        # Prepare values (nur neueste Werte, nicht alle)
        latest_features = features.tail(10)  # Letzte 10 Bars

        values = []
        for timestamp, row in latest_features.iterrows():
            values.append((
                symbol,
                timestamp,
                timeframe,
                float(row['sma_10']) if not pd.isna(row['sma_10']) else None,
                float(row['sma_20']) if not pd.isna(row['sma_20']) else None,
                float(row['sma_50']) if not pd.isna(row['sma_50']) else None,
                float(row['ema_10']) if not pd.isna(row['ema_10']) else None,
                float(row['ema_20']) if not pd.isna(row['ema_20']) else None,
                float(row['rsi_14']) if not pd.isna(row['rsi_14']) else None,
                float(row['macd']) if not pd.isna(row['macd']) else None,
                float(row['macd_signal']) if not pd.isna(row['macd_signal']) else None,
                float(row['macd_hist']) if not pd.isna(row['macd_hist']) else None,
                float(row['bb_upper']) if not pd.isna(row['bb_upper']) else None,
                float(row['bb_middle']) if not pd.isna(row['bb_middle']) else None,
                float(row['bb_lower']) if not pd.isna(row['bb_lower']) else None,
                float(row['atr_14']) if not pd.isna(row['atr_14']) else None
            ))

        try:
            self.db.execute_many(insert_sql, values)
            self.stats['features_calculated'] += len(values)
        except Exception as e:
            log_exception(self.logger, e, f"Failed to save features for {symbol} {timeframe}")
            self.stats['errors'] += 1

    def process_symbol_timeframe(self, symbol: str, timeframe: str):
        """
        Verarbeitet Symbol + Timeframe

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
        """
        try:
            # Fetch bars
            df = self.fetch_bars(symbol, timeframe, limit=200)

            if df is None or len(df) < 50:
                return

            # Calculate features
            features = self.calculate_features(df)

            if features is None:
                return

            # Save features
            self.save_features(symbol, timeframe, features)

        except Exception as e:
            log_exception(self.logger, e, f"Error processing {symbol} {timeframe}")
            self.stats['errors'] += 1

    def _calculate_loop(self):
        """Feature Calculation Loop (läuft in eigenem Thread)"""
        self.logger.info("Feature calculator started")

        calculation_interval = 60  # Sekunden (alle 60s neu berechnen)

        while self.is_running:
            try:
                # Process all symbols and timeframes
                for symbol in self.symbols:
                    for timeframe in self.timeframes:
                        self.process_symbol_timeframe(symbol, timeframe)

                # Log progress
                self.logger.info(f"Features calculated: {self.stats['features_calculated']}, Errors: {self.stats['errors']}")

                # Sleep
                time.sleep(calculation_interval)

            except Exception as e:
                log_exception(self.logger, e, "Error in feature calculation loop")
                time.sleep(10)

        self.logger.info("Feature calculator stopped")

    def start(self):
        """Startet den Feature Calculator"""
        if self.is_running:
            self.logger.warning("Feature calculator already running")
            return

        self.logger.info("Starting feature calculator...")

        self.is_running = True
        self.stats['start_time'] = datetime.now()

        # Start thread
        self.calculator_thread = threading.Thread(target=self._calculate_loop, daemon=True)
        self.calculator_thread.start()

        self.logger.info(f"✓ Feature calculator started for {len(self.symbols)} symbols x {len(self.timeframes)} timeframes")

    def stop(self):
        """Stoppt den Feature Calculator"""
        if not self.is_running:
            return

        self.logger.info("Stopping feature calculator...")

        self.is_running = False

        # Wait for thread
        if self.calculator_thread:
            self.calculator_thread.join(timeout=10)

        # Log statistics
        self._log_statistics()

        self.logger.info("✓ Feature calculator stopped")

    def _log_statistics(self):
        """Loggt Statistiken"""
        if self.stats['start_time']:
            runtime = (datetime.now() - self.stats['start_time']).total_seconds()

            self.logger.info("=== Feature Calculator Statistics ===")
            self.logger.info(f"Runtime: {runtime:.0f}s")
            self.logger.info(f"Features Calculated: {self.stats['features_calculated']}")
            self.logger.info(f"Errors: {self.stats['errors']}")

    def get_latest_features(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """
        Holt neueste Features

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe

        Returns:
            Features Dictionary oder None
        """
        query = """
            SELECT *
            FROM features
            WHERE symbol = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """

        return self.db.fetch_dict(query, (symbol, timeframe))

    def __enter__(self):
        """Context Manager Enter"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Exit"""
        self.stop()


if __name__ == "__main__":
    # Test
    print("=== Feature Calculator Test ===\n")

    try:
        calculator = FeatureCalculator(symbols=['EURUSD'], timeframes=['1m', '5m'])

        # Calculate once
        print("Calculating features...")
        calculator.process_symbol_timeframe('EURUSD', '1m')

        # Get latest features
        print("\nLatest Features:")
        features = calculator.get_latest_features('EURUSD', '1m')
        if features:
            for key, value in features.items():
                if key not in ['symbol', 'timeframe', 'created_at']:
                    print(f"  {key}: {value}")

    except Exception as e:
        print(f"Error: {e}")

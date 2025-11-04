# -*- coding: utf-8 -*-
"""
Data Loader for ML Training
- Loads bar data with labels
- Creates sequences (sliding window)
- Train/Val/Test splits
- Batch generation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Optional
from sklearn.model_selection import train_test_split
from src.data.database_manager import get_database
from src.ml.label_engineering import LabelEngineer


class DataLoader:
    """Loads and preprocesses data for ML training"""

    def __init__(
        self,
        lookback_window: int = 10,
        pip_value: float = 0.0001,
        min_profit_pips: float = 1.5
    ):
        """
        Args:
            lookback_window: Number of past bars to use as features
            pip_value: Value of one pip
            min_profit_pips: Minimum profit threshold for labels
        """
        self.lookback_window = lookback_window
        self.label_engineer = LabelEngineer(pip_value, min_profit_pips)
        self.db = get_database('remote')  # Geändert auf 'remote' für trading_db

    def load_bar_data(
        self,
        symbol: str,
        timeframe: str = '1m',
        limit: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Load bar data from database

        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            timeframe: Bar timeframe
            limit: Maximum number of bars to load

        Returns:
            DataFrame with bar data or None
        """
        table = f"bars_{symbol.lower()}"

        sql = f"""
            SELECT
                timestamp,
                timeframe,
                open,
                high,
                low,
                close,
                volume,
                tick_count,
                rsi14,
                macd_main,
                bb_upper,
                bb_lower,
                atr14
            FROM {table}
            WHERE timeframe = %s
            ORDER BY timestamp ASC
        """

        if limit:
            sql += f" LIMIT {limit}"

        try:
            result = self.db.fetch_all(sql, (timeframe,))

            if not result:
                return None

            columns = ['timestamp', 'timeframe', 'open', 'high', 'low', 'close',
                      'volume', 'tick_count', 'rsi14', 'macd_main',
                      'bb_upper', 'bb_lower', 'atr14']

            df = pd.DataFrame(result, columns=columns)
            return df

        except Exception as e:
            print(f"Error loading bars for {symbol}: {e}")
            return None

    def load_training_data(
        self,
        symbols: List[str],
        timeframe: str = '1m',
        with_labels: bool = True,
        horizons: List[float] = None
    ) -> pd.DataFrame:
        """
        Load training data for multiple symbols

        Args:
            symbols: List of symbols to load
            timeframe: Bar timeframe
            with_labels: Whether to generate labels
            horizons: Time horizons for labels (in minutes)

        Returns:
            Combined DataFrame with all symbols
        """
        if horizons is None:
            horizons = [0.5, 1.0, 3.0, 5.0, 10.0]

        all_data = []

        for symbol in symbols:
            df = self.load_bar_data(symbol, timeframe)

            if df is None or len(df) == 0:
                continue

            # Add symbol column
            df['symbol'] = symbol

            # Generate labels if requested
            if with_labels:
                df = self.label_engineer.create_labels_from_timeframe(
                    df, timeframe, horizons
                )

            all_data.append(df)

        if not all_data:
            return pd.DataFrame()

        # Combine all symbols
        combined = pd.concat(all_data, ignore_index=True)
        return combined

    def create_flat_features(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        label_col: str,
        lookback: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create flattened features (for traditional ML models like XGBoost)

        Instead of sequences, creates flat feature vectors by including
        current + lagged features

        Args:
            df: DataFrame with data
            feature_cols: List of feature column names
            label_col: Label column name
            lookback: Number of lags to include

        Returns:
            (X, y) tuple where X is (samples, features * (lookback+1)) and y is (samples,)
        """
        if lookback is None:
            lookback = self.lookback_window

        # Remove rows with NaN labels
        df = df.dropna(subset=[label_col])

        if len(df) < lookback + 1:
            return np.array([]), np.array([])

        X_flat = []
        y_labels = []

        for i in range(lookback, len(df)):
            # Flatten: [current_features, lag1_features, lag2_features, ...]
            flat_features = []

            for lag in range(lookback + 1):
                idx = i - lag
                row_features = df.iloc[idx][feature_cols].values
                flat_features.extend(row_features)

            label = df.iloc[i][label_col]

            X_flat.append(flat_features)
            y_labels.append(label)

        return np.array(X_flat), np.array(y_labels)

    def train_val_test_split(
        self,
        X: np.ndarray,
        y: np.ndarray,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        shuffle: bool = False
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Split data into train/validation/test sets

        Args:
            X: Feature array
            y: Label array
            train_ratio: Training set ratio
            val_ratio: Validation set ratio
            test_ratio: Test set ratio
            shuffle: Whether to shuffle (usually False for time series)

        Returns:
            (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
            "Ratios must sum to 1.0"

        n_samples = len(X)
        n_train = int(n_samples * train_ratio)
        n_val = int(n_samples * val_ratio)

        if shuffle:
            indices = np.random.permutation(n_samples)
            X = X[indices]
            y = y[indices]

        X_train = X[:n_train]
        y_train = y[:n_train]

        X_val = X[n_train:n_train + n_val]
        y_val = y[n_train:n_train + n_val]

        X_test = X[n_train + n_val:]
        y_test = y[n_train + n_val:]

        return X_train, X_val, X_test, y_train, y_val, y_test


def demo():
    """Demo data loader"""
    from src.utils.config_loader import get_config

    print("="*70)
    print("DATA LOADER DEMO")
    print("="*70)

    config = get_config()
    symbols = config.get_symbols()

    # Initialize loader
    loader = DataLoader(lookback_window=10, min_profit_pips=1.5)

    # Load training data
    print(f"\nLoading data for {len(symbols)} symbols...")
    df = loader.load_training_data(symbols, timeframe='1m')

    print(f"Total samples loaded: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst few rows:")
    print(df.head())

    # Check label distribution
    label_cols = [col for col in df.columns if col.startswith('label_h')]
    print(f"\nLabel columns: {label_cols}")

    for col in label_cols:
        if col in df.columns:
            valid = df[col].dropna()
            if len(valid) > 0:
                up_pct = (valid == 1).sum() / len(valid) * 100
                print(f"{col}: {up_pct:.1f}% UP")

    # Create flat features for XGBoost
    feature_cols = ['open', 'high', 'low', 'close', 'volume',
                   'rsi14', 'macd_main', 'bb_upper', 'bb_lower', 'atr14']

    print(f"\n\nCreating flat features with {feature_cols}...")
    X, y = loader.create_flat_features(df, feature_cols, 'label_h5', lookback=5)

    print(f"X shape: {X.shape}")  # (samples, features * (lookback+1))
    print(f"y shape: {y.shape}")  # (samples,)

    if len(X) > 0:
        # Split data
        X_train, X_val, X_test, y_train, y_val, y_test = \
            loader.train_val_test_split(X, y)

        print(f"\nTrain set: {len(X_train)} samples")
        print(f"Val set: {len(X_val)} samples")
        print(f"Test set: {len(X_test)} samples")

        print(f"\nTrain labels - UP: {(y_train == 1).sum()}, DOWN: {(y_train == 0).sum()}")
        print(f"Val labels - UP: {(y_val == 1).sum()}, DOWN: {(y_val == 0).sum()}")
        print(f"Test labels - UP: {(y_test == 1).sum()}, DOWN: {(y_test == 0).sum()}")


if __name__ == '__main__':
    demo()

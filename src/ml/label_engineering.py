"""
Label Engineering for ML Training
- Multi-horizon price movement labels
- Binary classification (UP/DOWN)
- Profit-based thresholds
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from datetime import timedelta


class LabelEngineer:
    """Creates training labels from bar data"""

    def __init__(self, pip_value: float = 0.0001, min_profit_pips: float = 3.0):
        """
        Args:
            pip_value: Value of one pip (0.0001 for most forex pairs)
            min_profit_pips: Minimum profit in pips to consider as UP
        """
        self.pip_value = pip_value
        self.min_profit_pips = min_profit_pips
        self.profit_threshold = min_profit_pips * pip_value

    def create_binary_labels(
        self,
        df: pd.DataFrame,
        horizons: List[int],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        Create binary labels (1=UP, 0=DOWN) for multiple horizons

        Args:
            df: DataFrame with bar data (must be sorted by timestamp)
            horizons: List of forward-looking bar counts (e.g., [1, 2, 3, 5, 10])
            price_col: Column name for price

        Returns:
            DataFrame with added label columns: label_h1, label_h2, etc.
        """
        df = df.copy()

        for horizon in horizons:
            label_col = f'label_h{horizon}'

            # Calculate future price
            future_price = df[price_col].shift(-horizon)

            # Calculate price change
            price_change = (future_price - df[price_col]) / df[price_col]

            # Binary label: 1 if price goes up by at least threshold, 0 otherwise
            df[label_col] = (price_change >= self.profit_threshold).astype(int)

            # Mark rows where we can't calculate future price (end of data)
            df.loc[df.index[-horizon:], label_col] = np.nan

        return df

    def create_regression_labels(
        self,
        df: pd.DataFrame,
        horizons: List[int],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        Create regression labels (actual price change) for multiple horizons

        Args:
            df: DataFrame with bar data
            horizons: List of forward-looking bar counts
            price_col: Column name for price

        Returns:
            DataFrame with added target columns: target_h1, target_h2, etc.
        """
        df = df.copy()

        for horizon in horizons:
            target_col = f'target_h{horizon}'

            # Calculate future price
            future_price = df[price_col].shift(-horizon)

            # Calculate price change (percentage)
            df[target_col] = (future_price - df[price_col]) / df[price_col]

            # Mark rows where we can't calculate future price
            df.loc[df.index[-horizon:], target_col] = np.nan

        return df

    def create_multi_class_labels(
        self,
        df: pd.DataFrame,
        horizons: List[int],
        price_col: str = 'close',
        thresholds: Tuple[float, float] = None
    ) -> pd.DataFrame:
        """
        Create multi-class labels (0=DOWN, 1=NEUTRAL, 2=UP) for multiple horizons

        Args:
            df: DataFrame with bar data
            horizons: List of forward-looking bar counts
            price_col: Column name for price
            thresholds: (lower, upper) thresholds for classification
                       Default: (-profit_threshold, +profit_threshold)

        Returns:
            DataFrame with added label columns: label_h1, label_h2, etc.
        """
        if thresholds is None:
            thresholds = (-self.profit_threshold, self.profit_threshold)

        df = df.copy()
        lower_threshold, upper_threshold = thresholds

        for horizon in horizons:
            label_col = f'label_h{horizon}'

            # Calculate future price
            future_price = df[price_col].shift(-horizon)

            # Calculate price change
            price_change = (future_price - df[price_col]) / df[price_col]

            # Multi-class label
            df[label_col] = 1  # Default: NEUTRAL
            df.loc[price_change < lower_threshold, label_col] = 0  # DOWN
            df.loc[price_change > upper_threshold, label_col] = 2  # UP

            # Mark rows where we can't calculate future price
            df.loc[df.index[-horizon:], label_col] = np.nan

        return df

    def create_labels_from_timeframe(
        self,
        df: pd.DataFrame,
        timeframe: str,
        target_minutes: List[float]
    ) -> pd.DataFrame:
        """
        Create labels based on time-based horizons instead of bar counts

        Args:
            df: DataFrame with bar data
            timeframe: Current timeframe ('1m', '5m', '15m', '1h', '4h')
            target_minutes: List of forward-looking minutes (e.g., [0.5, 1, 3, 5, 10])

        Returns:
            DataFrame with labels for each time horizon
        """
        # Map timeframe to minutes
        tf_to_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240
        }

        bars_per_minute = 1 / tf_to_minutes[timeframe]

        # Convert minutes to bar counts
        horizons = [int(minutes * bars_per_minute) for minutes in target_minutes]
        horizons = [max(1, h) for h in horizons]  # Ensure at least 1 bar

        return self.create_binary_labels(df, horizons)

    def analyze_label_distribution(
        self,
        df: pd.DataFrame,
        label_cols: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Analyze label distribution to detect class imbalance

        Args:
            df: DataFrame with labels
            label_cols: List of label column names

        Returns:
            Dictionary with distribution stats per label
        """
        stats = {}

        for col in label_cols:
            if col not in df.columns:
                continue

            valid_data = df[col].dropna()
            total = len(valid_data)

            if total == 0:
                stats[col] = {'total': 0, 'up': 0, 'down': 0, 'balance': 0.0}
                continue

            up_count = (valid_data == 1).sum()
            down_count = (valid_data == 0).sum()

            stats[col] = {
                'total': total,
                'up': up_count,
                'down': down_count,
                'up_pct': round(up_count / total * 100, 2),
                'down_pct': round(down_count / total * 100, 2),
                'balance': round(min(up_count, down_count) / max(up_count, down_count, 1), 2)
            }

        return stats

    def apply_class_balancing(
        self,
        df: pd.DataFrame,
        label_col: str,
        method: str = 'undersample'
    ) -> pd.DataFrame:
        """
        Balance classes by undersampling or oversampling

        Args:
            df: DataFrame with labels
            label_col: Label column name
            method: 'undersample' or 'oversample'

        Returns:
            Balanced DataFrame
        """
        if label_col not in df.columns:
            return df

        df = df.dropna(subset=[label_col])

        up_df = df[df[label_col] == 1]
        down_df = df[df[label_col] == 0]

        if method == 'undersample':
            # Undersample majority class
            min_count = min(len(up_df), len(down_df))
            up_df = up_df.sample(n=min_count, random_state=42)
            down_df = down_df.sample(n=min_count, random_state=42)
        elif method == 'oversample':
            # Oversample minority class
            max_count = max(len(up_df), len(down_df))
            up_df = up_df.sample(n=max_count, replace=True, random_state=42)
            down_df = down_df.sample(n=max_count, replace=True, random_state=42)

        balanced_df = pd.concat([up_df, down_df], ignore_index=True)
        return balanced_df.sample(frac=1, random_state=42).reset_index(drop=True)


def demo():
    """Demo label engineering"""
    # Create sample data
    dates = pd.date_range('2025-01-01', periods=100, freq='1min')
    prices = np.cumsum(np.random.randn(100)) * 0.0001 + 1.1000

    df = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'rsi14': np.random.uniform(30, 70, 100)
    })

    print("Sample Data:")
    print(df.head())
    print()

    # Create label engineer
    engineer = LabelEngineer(pip_value=0.0001, min_profit_pips=3)

    # Create binary labels
    horizons = [1, 2, 3, 5, 10]  # 1, 2, 3, 5, 10 bars ahead
    df_labeled = engineer.create_binary_labels(df, horizons)

    print("Data with Labels:")
    print(df_labeled[['timestamp', 'close', 'label_h1', 'label_h3', 'label_h5']].head(20))
    print()

    # Analyze label distribution
    label_cols = [f'label_h{h}' for h in horizons]
    stats = engineer.analyze_label_distribution(df_labeled, label_cols)

    print("Label Distribution:")
    for col, stat in stats.items():
        print(f"{col}: UP={stat['up_pct']}%, DOWN={stat['down_pct']}%, Balance={stat['balance']}")
    print()

    # Create multi-class labels
    df_multi = engineer.create_multi_class_labels(df, [5])
    print("Multi-class Labels (0=DOWN, 1=NEUTRAL, 2=UP):")
    print(df_multi[['timestamp', 'close', 'label_h5']].head(20))


if __name__ == '__main__':
    demo()

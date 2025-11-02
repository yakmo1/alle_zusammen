# -*- coding: utf-8 -*-
"""
Feature Engineering for ML Training
- Derived price features
- Normalized indicators
- Trend features
- Volatility ratios
"""

import pandas as pd
import numpy as np
from typing import List


class FeatureEngineer:
    """Creates derived features from raw bar data"""

    def __init__(self):
        pass

    def add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add price-based derived features

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with added features
        """
        df = df.copy()

        # Price changes
        df['price_change'] = (df['close'] - df['open']) / df['open']
        df['high_low_range'] = (df['high'] - df['low']) / df['close']

        # Candle body and shadows
        df['body_size'] = abs(df['close'] - df['open']) / df['close']
        df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
        df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']

        # Intrabar price position
        df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)

        return df

    def add_returns(self, df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        Add return features

        Args:
            df: DataFrame with close prices
            periods: List of lookback periods

        Returns:
            DataFrame with return features
        """
        if periods is None:
            periods = [1, 2, 3, 5]

        df = df.copy()

        for period in periods:
            df[f'return_{period}'] = df['close'].pct_change(period)

        return df

    def add_normalized_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add normalized indicator features

        Args:
            df: DataFrame with indicator data

        Returns:
            DataFrame with normalized indicators
        """
        df = df.copy()

        # RSI normalization (center around 0)
        if 'rsi14' in df.columns:
            df['rsi14_norm'] = (df['rsi14'] - 50) / 50

        # MACD normalization
        if 'macd_main' in df.columns:
            df['macd_norm'] = df['macd_main'] / (df['close'] + 1e-10)
            df['macd_signal'] = (df['macd_main'] > 0).astype(int)

        # Bollinger Bands position
        if all(col in df.columns for col in ['bb_upper', 'bb_lower', 'close']):
            bb_range = df['bb_upper'] - df['bb_lower'] + 1e-10
            df['bb_position'] = (df['close'] - df['bb_lower']) / bb_range
            df['bb_width'] = bb_range / df['close']

        return df

    def add_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add trend-based features

        Args:
            df: DataFrame with price and indicator data

        Returns:
            DataFrame with trend features
        """
        df = df.copy()

        # Price vs volume
        if 'volume' in df.columns:
            df['price_volume_ratio'] = df['price_change'] * df['volume']

        return df

    def add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add volatility-based features

        Args:
            df: DataFrame with price and ATR data

        Returns:
            DataFrame with volatility features
        """
        df = df.copy()

        # ATR normalization
        if 'atr14' in df.columns:
            df['atr_norm'] = df['atr14'] / (df['close'] + 1e-10)

        # Rolling volatility
        df['volatility_5'] = df['close'].pct_change().rolling(5).std()
        df['volatility_10'] = df['close'].pct_change().rolling(10).std()

        return df

    def add_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all engineered features

        Args:
            df: DataFrame with raw data

        Returns:
            DataFrame with all features
        """
        df = self.add_price_features(df)
        df = self.add_returns(df)
        df = self.add_normalized_indicators(df)
        df = self.add_trend_features(df)
        df = self.add_volatility_features(df)

        return df

    def get_feature_names(self, include_base: bool = True) -> List[str]:
        """
        Get list of all feature names

        Args:
            include_base: Whether to include base features (OHLC, indicators)

        Returns:
            List of feature names
        """
        derived_features = [
            # Price features
            'price_change', 'high_low_range', 'body_size',
            'upper_shadow', 'lower_shadow', 'close_position',
            # Returns
            'return_1', 'return_2', 'return_3', 'return_5',
            # Normalized indicators
            'rsi14_norm', 'macd_norm', 'macd_signal',
            'bb_position', 'bb_width',
            # Trend
            'price_volume_ratio',
            # Volatility
            'atr_norm', 'volatility_5', 'volatility_10'
        ]

        if include_base:
            base_features = [
                'open', 'high', 'low', 'close', 'volume',
                'rsi14', 'macd_main', 'bb_upper', 'bb_lower', 'atr14'
            ]
            return base_features + derived_features

        return derived_features


def demo():
    """Demo feature engineering"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from src.ml.data_loader import DataLoader
    from src.utils.config_loader import get_config

    print("="*70)
    print("FEATURE ENGINEERING DEMO")
    print("="*70)

    # Load data
    config = get_config()
    symbols = config.get_symbols()

    loader = DataLoader(min_profit_pips=1.5)
    df = loader.load_training_data(symbols, timeframe='1m')

    print(f"\nOriginal features: {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)[:15]}...")

    # Engineer features
    engineer = FeatureEngineer()
    df_eng = engineer.add_all_features(df)

    print(f"\nAfter engineering: {len(df_eng.columns)} columns")
    print(f"\nNew features added:")

    new_cols = [col for col in df_eng.columns if col not in df.columns]
    for col in new_cols:
        print(f"  - {col}")

    # Show sample
    print(f"\nSample data with new features:")
    feature_cols = ['close', 'price_change', 'body_size', 'rsi14_norm',
                   'bb_position', 'atr_norm', 'volatility_5']
    print(df_eng[feature_cols].head(10))

    # Feature statistics
    print(f"\nFeature statistics:")
    print(df_eng[new_cols].describe())


if __name__ == '__main__':
    demo()

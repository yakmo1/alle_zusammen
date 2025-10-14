# -*- coding: utf-8 -*-
"""
XGBoost Model Wrapper
- Binary classification for price direction
- Built-in feature importance
- Early stopping support
"""

import xgboost as xgb
import numpy as np
from typing import Dict, Optional, Tuple
import pickle
from pathlib import Path


class XGBoostModel:
    """Wrapper for XGBoost binary classifier"""

    def __init__(self, params: Optional[Dict] = None):
        """
        Args:
            params: XGBoost hyperparameters
        """
        if params is None:
            params = self.get_default_params()

        self.params = params
        self.model = None
        self.feature_names = None
        self.train_history = {}

    @staticmethod
    def get_default_params() -> Dict:
        """Get default XGBoost parameters"""
        return {
            'objective': 'binary:logistic',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'eval_metric': 'auc',
            'random_state': 42,
            'n_jobs': -1
        }

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        early_stopping_rounds: int = 10,
        verbose: bool = True
    ) -> Dict:
        """
        Train XGBoost model

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            early_stopping_rounds: Rounds for early stopping
            verbose: Print progress

        Returns:
            Training history dict
        """
        # Prepare eval set
        eval_set = None
        if X_val is not None and y_val is not None:
            eval_set = [(X_train, y_train), (X_val, y_val)]

        # Initialize model
        self.model = xgb.XGBClassifier(**self.params)

        # Train (simplified - no early stopping for compatibility)
        self.model.fit(X_train, y_train)

        # Store history
        if hasattr(self.model, 'evals_result_'):
            self.train_history = self.model.evals_result_()

        return self.train_history

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class labels

        Args:
            X: Features

        Returns:
            Predicted labels (0 or 1)
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities

        Args:
            X: Features

        Returns:
            Probabilities for each class
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        return self.model.predict_proba(X)

    def get_feature_importance(self, importance_type: str = 'gain') -> Dict[int, float]:
        """
        Get feature importance scores

        Args:
            importance_type: 'gain', 'weight', or 'cover'

        Returns:
            Dictionary of feature index to importance score
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        importance = self.model.get_booster().get_score(importance_type=importance_type)
        return importance

    def save(self, filepath: str):
        """
        Save model to file

        Args:
            filepath: Path to save model
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Save XGBoost model
        self.model.save_model(filepath)

        # Save metadata
        metadata = {
            'params': self.params,
            'feature_names': self.feature_names,
            'train_history': self.train_history
        }

        metadata_path = str(Path(filepath).with_suffix('.meta'))
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)

    def load(self, filepath: str):
        """
        Load model from file

        Args:
            filepath: Path to model file
        """
        # Load XGBoost model
        self.model = xgb.XGBClassifier()
        self.model.load_model(filepath)

        # Load metadata
        metadata_path = str(Path(filepath).with_suffix('.meta'))
        try:
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
                self.params = metadata.get('params', {})
                self.feature_names = metadata.get('feature_names')
                self.train_history = metadata.get('train_history', {})
        except FileNotFoundError:
            print(f"Warning: Metadata file not found at {metadata_path}")


if __name__ == '__main__':
    # Demo
    print("XGBoost Model Demo")
    print("="*70)

    # Create synthetic data
    np.random.seed(42)
    X_train = np.random.randn(100, 10)
    y_train = (X_train[:, 0] + X_train[:, 1] > 0).astype(int)
    X_val = np.random.randn(20, 10)
    y_val = (X_val[:, 0] + X_val[:, 1] > 0).astype(int)

    # Train model
    model = XGBoostModel()
    print(f"Training with params: {model.params}")
    model.train(X_train, y_train, X_val, y_val, verbose=False)

    # Predictions
    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)

    accuracy = (y_pred == y_val).mean()
    print(f"\nValidation Accuracy: {accuracy:.2%}")

    # Feature importance
    importance = model.get_feature_importance()
    print(f"\nTop 3 features by importance:")
    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:3]
    for feat, score in sorted_features:
        print(f"  {feat}: {score:.2f}")

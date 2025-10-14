"""
Signal Generator
Generiert Trading Signals aus ML Predictions
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config
from ..data.database_manager import get_database


class SignalGenerator:
    """Generiert Trading Signals aus ML Predictions"""

    def __init__(self, db_type: str = 'local'):
        """
        Initialisiert den Signal Generator

        Args:
            db_type: Database Type
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)

        # Configuration
        self.min_confidence = 0.60  # Minimum 60% Confidence
        self.min_agreement_ratio = 0.6  # 60% der Horizons müssen übereinstimmen

        # Horizons gewichtet (kürzere Horizons haben weniger Gewicht)
        self.horizon_weights = {
            30: 0.5,   # 30s: 50% Gewicht
            60: 0.7,   # 1m: 70% Gewicht
            180: 1.0,  # 3m: 100% Gewicht
            300: 1.0,  # 5m: 100% Gewicht
            600: 0.8   # 10m: 80% Gewicht
        }

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
            limit: Anzahl Predictions pro Horizon

        Returns:
            Liste von Predictions
        """
        query = """
            SELECT
                timestamp, symbol, timeframe, prediction_horizon,
                current_price, predicted_price, signal, confidence,
                algorithm, model_version
            FROM model_forecasts
            WHERE symbol = %s
              AND timeframe = %s
              AND timestamp >= NOW() - INTERVAL '5 minutes'
            ORDER BY timestamp DESC, prediction_horizon
            LIMIT %s
        """

        return self.db.fetch_all_dict(query, (symbol, timeframe, limit * 5))

    def analyze_multi_horizon_predictions(
        self,
        predictions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analysiert Predictions über mehrere Horizons

        Args:
            predictions: Liste von Predictions

        Returns:
            Aggregierte Analyse
        """
        if not predictions:
            return None

        # Group by horizon
        by_horizon = {}
        for pred in predictions:
            horizon = pred['prediction_horizon']
            if horizon not in by_horizon:
                by_horizon[horizon] = []
            by_horizon[horizon].append(pred)

        # Analyze each horizon
        horizon_signals = {}
        for horizon, preds in by_horizon.items():
            # Get latest prediction for this horizon
            latest = preds[0]

            # Weight by horizon
            weight = self.horizon_weights.get(horizon, 0.5)

            horizon_signals[horizon] = {
                'signal': latest['signal'],
                'confidence': latest['confidence'],
                'price_change': (latest['predicted_price'] - latest['current_price']) / latest['current_price'],
                'weight': weight,
                'weighted_confidence': latest['confidence'] * weight
            }

        # Aggregate signals
        total_weight = sum(h['weight'] for h in horizon_signals.values())
        weighted_confidence = sum(h['weighted_confidence'] for h in horizon_signals.values()) / total_weight if total_weight > 0 else 0

        # Count signal types
        buy_count = sum(1 for h in horizon_signals.values() if h['signal'] == 'BUY')
        sell_count = sum(1 for h in horizon_signals.values() if h['signal'] == 'SELL')
        hold_count = sum(1 for h in horizon_signals.values() if h['signal'] == 'HOLD')

        total_count = len(horizon_signals)

        # Determine consensus signal
        if buy_count / total_count >= self.min_agreement_ratio:
            consensus_signal = 'BUY'
        elif sell_count / total_count >= self.min_agreement_ratio:
            consensus_signal = 'SELL'
        else:
            consensus_signal = 'HOLD'

        return {
            'symbol': predictions[0]['symbol'],
            'timeframe': predictions[0]['timeframe'],
            'timestamp': datetime.now(),
            'consensus_signal': consensus_signal,
            'confidence': weighted_confidence,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': hold_count,
            'total_horizons': total_count,
            'agreement_ratio': max(buy_count, sell_count, hold_count) / total_count,
            'horizon_signals': horizon_signals,
            'current_price': predictions[0]['current_price']
        }

    def generate_signal(
        self,
        symbol: str,
        timeframe: str = '1m'
    ) -> Optional[Dict[str, Any]]:
        """
        Generiert Trading Signal

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe

        Returns:
            Trading Signal Dictionary oder None
        """
        try:
            # Get latest predictions
            predictions = self.get_latest_predictions(symbol, timeframe)

            if not predictions:
                self.logger.warning(f"No predictions available for {symbol} {timeframe}")
                return None

            # Analyze multi-horizon
            analysis = self.analyze_multi_horizon_predictions(predictions)

            if not analysis:
                return None

            # Check confidence threshold
            if analysis['confidence'] < self.min_confidence:
                self.logger.info(
                    f"Signal confidence too low for {symbol}: {analysis['confidence']:.3f} "
                    f"(minimum: {self.min_confidence})"
                )
                return None

            # Check agreement ratio
            if analysis['agreement_ratio'] < self.min_agreement_ratio:
                self.logger.info(
                    f"Signal agreement too low for {symbol}: {analysis['agreement_ratio']:.3f} "
                    f"(minimum: {self.min_agreement_ratio})"
                )
                return None

            # Skip HOLD signals
            if analysis['consensus_signal'] == 'HOLD':
                return None

            # Calculate entry, stop loss, and take profit
            current_price = analysis['current_price']
            signal_type = analysis['consensus_signal']

            # Get ATR for stop loss calculation
            atr = self._get_latest_atr(symbol, timeframe)
            if not atr:
                atr = current_price * 0.001  # Default: 0.1%

            # Calculate stop loss and take profit
            if signal_type == 'BUY':
                stop_loss = current_price - (atr * 2)  # 2 ATR
                take_profit = current_price + (atr * 3)  # 3 ATR (1.5 R/R)
            else:  # SELL
                stop_loss = current_price + (atr * 2)
                take_profit = current_price - (atr * 3)

            # Create signal
            signal = {
                'symbol': symbol,
                'timeframe': timeframe,
                'timestamp': datetime.now(),
                'signal': signal_type,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': analysis['confidence'],
                'agreement_ratio': analysis['agreement_ratio'],
                'risk_reward_ratio': 1.5,
                'horizon_details': analysis['horizon_signals'],
                'buy_count': analysis['buy_count'],
                'sell_count': analysis['sell_count'],
                'hold_count': analysis['hold_count']
            }

            # Save signal to database
            self._save_signal(signal)

            self.logger.info(
                f"Generated {signal_type} signal for {symbol} @ {current_price:.5f} "
                f"(Confidence: {analysis['confidence']:.3f}, Agreement: {analysis['agreement_ratio']:.3f})"
            )

            return signal

        except Exception as e:
            log_exception(self.logger, e, f"Failed to generate signal for {symbol}")
            return None

    def _get_latest_atr(self, symbol: str, timeframe: str) -> Optional[float]:
        """
        Holt neuesten ATR-Wert

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe

        Returns:
            ATR value or None
        """
        query = """
            SELECT atr_14
            FROM features
            WHERE symbol = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """

        result = self.db.fetch_dict(query, (symbol, timeframe))
        if result and result['atr_14']:
            return float(result['atr_14'])

        return None

    def _save_signal(self, signal: Dict[str, Any]):
        """
        Speichert Signal in Database

        Args:
            signal: Signal Dictionary
        """
        try:
            insert_sql = """
                INSERT INTO signals
                    (timestamp, symbol, timeframe, signal_type,
                     entry_price, stop_loss, take_profit,
                     confidence, risk_reward_ratio, status)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            self.db.execute(insert_sql, (
                signal['timestamp'],
                signal['symbol'],
                signal['timeframe'],
                signal['signal'],
                signal['entry_price'],
                signal['stop_loss'],
                signal['take_profit'],
                signal['confidence'],
                signal['risk_reward_ratio'],
                'ACTIVE'
            ))

        except Exception as e:
            log_exception(self.logger, e, "Failed to save signal to database")

    def generate_signals_all_symbols(
        self,
        timeframe: str = '1m'
    ) -> List[Dict[str, Any]]:
        """
        Generiert Signals für alle Symbols

        Args:
            timeframe: Timeframe

        Returns:
            Liste von Signals
        """
        symbols = self.config.get_symbols()
        signals = []

        for symbol in symbols:
            signal = self.generate_signal(symbol, timeframe)
            if signal:
                signals.append(signal)

        return signals

    def get_active_signals(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Holt aktive Signals

        Args:
            symbol: Optional Symbol filter

        Returns:
            Liste von aktiven Signals
        """
        if symbol:
            query = """
                SELECT * FROM signals
                WHERE symbol = %s AND status = 'ACTIVE'
                ORDER BY timestamp DESC
                LIMIT 10
            """
            return self.db.fetch_all_dict(query, (symbol,))
        else:
            query = """
                SELECT * FROM signals
                WHERE status = 'ACTIVE'
                ORDER BY timestamp DESC
                LIMIT 50
            """
            return self.db.fetch_all_dict(query)


if __name__ == "__main__":
    # Test
    print("=== Signal Generator Test ===\n")

    generator = SignalGenerator()

    # Generate signal for EURUSD
    print("Generating signal for EURUSD...")
    signal = generator.generate_signal('EURUSD', '1m')

    if signal:
        print("\nGenerated Signal:")
        print(f"  Symbol: {signal['symbol']}")
        print(f"  Signal: {signal['signal']}")
        print(f"  Entry Price: {signal['entry_price']:.5f}")
        print(f"  Stop Loss: {signal['stop_loss']:.5f}")
        print(f"  Take Profit: {signal['take_profit']:.5f}")
        print(f"  Confidence: {signal['confidence']:.3f}")
        print(f"  Agreement Ratio: {signal['agreement_ratio']:.3f}")
        print(f"  Risk/Reward: {signal['risk_reward_ratio']:.2f}")
    else:
        print("\nNo signal generated (insufficient confidence or no predictions available)")

"""
Enhanced Trading Strategy Engine für MetaTrader 5
Implementiert verschiedene Trading-Strategien mit technischen Indikatoren
- Enhanced Forex Strategies
- Advanced Crypto 24/7 Trading  
- Multiple Timeframe Analysis
"""

import pandas as pd
import numpy as np
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import sys
import os

# Import crypto strategy
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from strategies.crypto_advanced_strategy import CryptoAdvancedStrategy
except ImportError:
    logging.warning("Could not import CryptoAdvancedStrategy, using fallback")
    CryptoAdvancedStrategy = None

class TradingStrategy(ABC):
    """Basis-Klasse für alle Trading-Strategien"""
    
    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params
        self.signals = []
        self.performance_metrics = {}
        
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Signal generieren basierend auf Marktdaten"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, account_info: Dict[str, Any], signal: Dict[str, Any]) -> float:
        """Positionsgröße berechnen"""
        pass
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Technische Indikatoren hinzufügen - Native Python Implementation"""
        try:
            # Simple Moving Averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # Exponential Moving Averages
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
            
            # RSI
            df['rsi'] = self.calculate_rsi(df['close'], 14)
            
            # Bollinger Bands
            bb_result = self.calculate_bollinger_bands(df['close'], 20, 2)
            df['bb_upper'] = bb_result['upper']
            df['bb_middle'] = bb_result['middle']
            df['bb_lower'] = bb_result['lower']
            
            # ATR
            df['atr'] = self.calculate_atr(df['high'], df['low'], df['close'], 14)
            
            # Stochastic
            stoch_result = self.calculate_stochastic(df['high'], df['low'], df['close'])
            df['stoch_k'] = stoch_result['%K']
            df['stoch_d'] = stoch_result['%D']
            
            return df
            
        except Exception as e:
            logging.error(f"Fehler beim Hinzufügen der Indikatoren: {e}")
            return df
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI Berechnung"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Bollinger Bands Berechnung"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return {'upper': upper, 'middle': middle, 'lower': lower}
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range Berechnung"""
        high_low = high - low
        high_close_prev = np.abs(high - close.shift())
        low_close_prev = np.abs(low - close.shift())
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Stochastic Oscillator Berechnung"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return {'%K': k_percent, '%D': d_percent}

class MACDRSIStrategy(TradingStrategy):
    """MACD + RSI Kombinations-Strategie"""
    
    def __init__(self):
        params = {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'risk_percent': 1.0,
            'stop_loss_atr_multiplier': 2.0,
            'take_profit_ratio': 2.0  # Risk-Reward 1:2
        }
        super().__init__("MACD_RSI_Strategy", params)
    
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Signal basierend auf MACD und RSI"""
        if len(data) < 50:
            return {'signal': 'HOLD', 'confidence': 0}
        
        # Letzte Werte
        current = data.iloc[-1]
        previous = data.iloc[-2]
        
        signal_type = 'HOLD'
        confidence = 0
        entry_price = current['close']
        stop_loss = 0
        take_profit = 0
        
        # BUY Signal: MACD bullish crossover + RSI oversold recovery
        if (current['macd'] > current['macd_signal'] and 
            previous['macd'] <= previous['macd_signal'] and
            current['rsi'] > 30 and current['rsi'] < 50):
            
            signal_type = 'BUY'
            confidence = self._calculate_confidence(data, 'BUY')
            stop_loss = entry_price - (current['atr'] * self.params['stop_loss_atr_multiplier'])
            take_profit = entry_price + ((entry_price - stop_loss) * self.params['take_profit_ratio'])
        
        # SELL Signal: MACD bearish crossover + RSI overbought decline
        elif (current['macd'] < current['macd_signal'] and 
              previous['macd'] >= previous['macd_signal'] and
              current['rsi'] < 70 and current['rsi'] > 50):
            
            signal_type = 'SELL'
            confidence = self._calculate_confidence(data, 'SELL')
            stop_loss = entry_price + (current['atr'] * self.params['stop_loss_atr_multiplier'])
            take_profit = entry_price - ((stop_loss - entry_price) * self.params['take_profit_ratio'])
        
        return {
            'signal': signal_type,
            'confidence': confidence,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': current['time'],
            'strategy': self.name
        }
    
    def _calculate_confidence(self, data: pd.DataFrame, signal_type: str) -> float:
        """Konfidenz-Level berechnen (0-100)"""
        confidence = 50  # Basis-Konfidenz
        
        current = data.iloc[-1]
        
        # Trend-Bestätigung durch Moving Averages
        if signal_type == 'BUY':
            if current['close'] > current['sma_20']:
                confidence += 15
            if current['sma_20'] > current['sma_50']:
                confidence += 10
            if current['rsi'] < 40:  # Noch im oversold Bereich
                confidence += 10
        
        elif signal_type == 'SELL':
            if current['close'] < current['sma_20']:
                confidence += 15
            if current['sma_20'] < current['sma_50']:
                confidence += 10
            if current['rsi'] > 60:  # Noch im overbought Bereich
                confidence += 10
        
        # Volatilität berücksichtigen
        if current['atr'] > data['atr'].rolling(20).mean().iloc[-1]:
            confidence -= 5  # Hohe Volatilität = weniger Konfidenz
        
        return min(confidence, 100)
    
    def calculate_position_size(self, account_info: Dict[str, Any], signal: Dict[str, Any]) -> float:
        """Positionsgröße basierend auf Risk Management"""
        if signal['signal'] == 'HOLD' or signal['confidence'] < 60:
            return 0
        
        account_balance = account_info.get('balance', 0)
        risk_amount = account_balance * (self.params['risk_percent'] / 100)
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        
        if stop_loss == 0 or entry_price == stop_loss:
            return 0
        
        # Risk per unit berechnen
        risk_per_unit = abs(entry_price - stop_loss)
        
        # Positionsgröße berechnen
        position_size = risk_amount / risk_per_unit
        
        # Mindest- und Höchstgrenzen
        min_size = 0.01
        max_size = account_balance * 0.1 / entry_price  # Max 10% des Kontos
        
        position_size = max(min_size, min(position_size, max_size))
        
        # Auf 2 Dezimalstellen runden
        return round(position_size, 2)

class BollingerBandStrategy(TradingStrategy):
    """Bollinger Band Mean Reversion Strategy"""
    
    def __init__(self):
        params = {
            'bb_period': 20,
            'bb_std': 2,
            'rsi_threshold': 30,
            'risk_percent': 1.0,
            'stop_loss_atr_multiplier': 1.5,
            'take_profit_ratio': 1.5
        }
        super().__init__("Bollinger_Band_Strategy", params)
    
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Signal basierend auf Bollinger Bands"""
        if len(data) < 30:
            return {'signal': 'HOLD', 'confidence': 0}
        
        current = data.iloc[-1]
        previous = data.iloc[-2]
        
        signal_type = 'HOLD'
        confidence = 0
        entry_price = current['close']
        stop_loss = 0
        take_profit = 0
        
        # BUY Signal: Preis berührt unteres BB + RSI oversold
        if (current['close'] <= current['bb_lower'] and 
            previous['close'] > previous['bb_lower'] and
            current['rsi'] < 35):
            
            signal_type = 'BUY'
            confidence = self._calculate_bb_confidence(data, 'BUY')
            stop_loss = current['bb_lower'] - (current['atr'] * self.params['stop_loss_atr_multiplier'])
            take_profit = current['bb_middle']
        
        # SELL Signal: Preis berührt oberes BB + RSI overbought
        elif (current['close'] >= current['bb_upper'] and 
              previous['close'] < previous['bb_upper'] and
              current['rsi'] > 65):
            
            signal_type = 'SELL'
            confidence = self._calculate_bb_confidence(data, 'SELL')
            stop_loss = current['bb_upper'] + (current['atr'] * self.params['stop_loss_atr_multiplier'])
            take_profit = current['bb_middle']
        
        return {
            'signal': signal_type,
            'confidence': confidence,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': current['time'],
            'strategy': self.name
        }
    
    def _calculate_bb_confidence(self, data: pd.DataFrame, signal_type: str) -> float:
        """Konfidenz für Bollinger Band Signale"""
        confidence = 55
        current = data.iloc[-1]
        
        # Volatilität prüfen
        bb_width = (current['bb_upper'] - current['bb_lower']) / current['bb_middle']
        avg_bb_width = ((data['bb_upper'] - data['bb_lower']) / data['bb_middle']).rolling(20).mean().iloc[-1]
        
        if bb_width > avg_bb_width:
            confidence += 10  # Hohe Volatilität = bessere BB-Signale
        
        # RSI-Bestätigung
        if signal_type == 'BUY' and current['rsi'] < 25:
            confidence += 15
        elif signal_type == 'SELL' and current['rsi'] > 75:
            confidence += 15
        
        return min(confidence, 100)
    
    def calculate_position_size(self, account_info: Dict[str, Any], signal: Dict[str, Any]) -> float:
        """Positionsgröße für BB-Strategie"""
        if signal['signal'] == 'HOLD' or signal['confidence'] < 55:
            return 0
        
        account_balance = account_info.get('balance', 0)
        risk_amount = account_balance * (self.params['risk_percent'] / 100)
        
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        
        if stop_loss == 0 or entry_price == stop_loss:
            return 0
        
        risk_per_unit = abs(entry_price - stop_loss)
        position_size = risk_amount / risk_per_unit
        
        min_size = 0.01
        max_size = account_balance * 0.08 / entry_price
        
        return round(max(min_size, min(position_size, max_size)), 2)

class StrategyManager:
    """Enhanced Strategy Manager mit Crypto 24/7 Support"""
    
    def __init__(self):
        # Traditional Strategies
        self.strategies = {}
        self.active_strategies = []
        
        # Enhanced Forex Strategies
        self.forex_strategies = {
            'macd_rsi': self._macd_rsi_strategy,
            'bollinger_momentum': self._bollinger_momentum_strategy,
            'trend_following': self._trend_following_strategy,
            'enhanced_rsi': self._enhanced_rsi_strategy,
            'multi_timeframe': self._multi_timeframe_strategy
        }
        
        # Advanced Crypto Strategy
        if CryptoAdvancedStrategy:
            self.crypto_strategy = CryptoAdvancedStrategy()
        else:
            self.crypto_strategy = None
            
        self.min_confidence = 0.55  # Lowered for more signals
        
        logging.info("Enhanced StrategyManager initialisiert mit %d Forex + Advanced Crypto Strategien", 
                    len(self.forex_strategies))
    
    def generate_signals(self, symbol: str, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Enhanced Signal Generation mit Crypto-Detection"""
        try:
            if data is None or data.empty or len(data) < 20:
                return []
            
            # Add technical indicators
            enhanced_data = self._add_enhanced_indicators(data)
            
            # Check if crypto symbol
            crypto_symbols = ['BTC', 'ETH', 'LTC', 'XRP', 'ADA', 'DOT', 'USDT', 'USD']
            is_crypto = any(crypto in symbol.upper() for crypto in crypto_symbols)
            
            if is_crypto and self.crypto_strategy:
                # Use advanced crypto strategy
                return self.crypto_strategy.generate_crypto_signals(symbol, enhanced_data)
            else:
                # Use enhanced forex strategies
                return self._generate_enhanced_forex_signals(symbol, enhanced_data)
                
        except Exception as e:
            logging.error(f"Enhanced Signal Generation Error {symbol}: {e}")
            return []
    
    def _generate_enhanced_forex_signals(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """Enhanced Forex Signal Generation"""
        signals = []
        
        try:
            # Multiple strategy analysis
            for strategy_name, strategy_func in self.forex_strategies.items():
                try:
                    signal = strategy_func(symbol, df)
                    if signal and signal.get('confidence', 0) >= self.min_confidence:
                        signals.append(signal)
                except Exception as e:
                    logging.error(f"Strategy {strategy_name} error: {e}")
            
            # Return best signal or consensus
            if len(signals) >= 2:
                consensus = self._build_forex_consensus(signals)
                if consensus:
                    return [consensus]
            
            if signals:
                best_signal = max(signals, key=lambda x: x.get('confidence', 0))
                return [best_signal]
            
            return []
            
        except Exception as e:
            logging.error(f"Enhanced Forex Signal Error: {e}")
            return []
    
    def _add_enhanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhanced Technical Indicators"""
        try:
            enhanced_df = df.copy()
            
            # Basic indicators
            enhanced_df['sma_20'] = enhanced_df['close'].rolling(window=20).mean()
            enhanced_df['sma_50'] = enhanced_df['close'].rolling(window=50).mean()
            enhanced_df['ema_12'] = enhanced_df['close'].ewm(span=12).mean()
            enhanced_df['ema_26'] = enhanced_df['close'].ewm(span=26).mean()
            
            # MACD
            enhanced_df['macd'] = enhanced_df['ema_12'] - enhanced_df['ema_26']
            enhanced_df['macd_signal'] = enhanced_df['macd'].ewm(span=9).mean()
            enhanced_df['macd_hist'] = enhanced_df['macd'] - enhanced_df['macd_signal']
            
            # RSI
            enhanced_df['rsi'] = self._calculate_rsi(enhanced_df['close'], 14)
            
            # Bollinger Bands
            bb = self._calculate_bollinger_bands(enhanced_df['close'])
            enhanced_df['bb_upper'] = bb['upper']
            enhanced_df['bb_middle'] = bb['middle']
            enhanced_df['bb_lower'] = bb['lower']
            
            # ATR
            enhanced_df['atr'] = self._calculate_atr(enhanced_df)
            
            return enhanced_df
            
        except Exception as e:
            logging.error(f"Enhanced Indicators Error: {e}")
            return df
    
    def _macd_rsi_strategy(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Enhanced MACD + RSI Strategy"""
        try:
            if len(df) < 30:
                return None
            
            current_macd = df['macd'].iloc[-1]
            current_signal = df['macd_signal'].iloc[-1]
            prev_macd = df['macd'].iloc[-2]
            prev_signal = df['macd_signal'].iloc[-2]
            current_rsi = df['rsi'].iloc[-1]
            
            signal = None
            confidence = 0.5
            
            # MACD Crossover + RSI confirmation
            if (current_macd > current_signal and prev_macd <= prev_signal and 
                25 <= current_rsi <= 45):
                signal = 'BUY'
                confidence = 0.65 + (45 - current_rsi) / 100
            elif (current_macd < current_signal and prev_macd >= prev_signal and 
                  55 <= current_rsi <= 75):
                signal = 'SELL'
                confidence = 0.65 + (current_rsi - 55) / 100
            
            if signal and confidence >= self.min_confidence:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': 'Enhanced_MACD_RSI',
                    'details': f'MACD: {current_macd:.6f} RSI: {current_rsi:.1f}'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"MACD RSI Strategy Error: {e}")
            return None
    
    def _enhanced_rsi_strategy(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Enhanced RSI with Multiple Timeframe Context"""
        try:
            if len(df) < 30:
                return None
            
            current_rsi = df['rsi'].iloc[-1]
            rsi_ma = df['rsi'].rolling(window=10).mean().iloc[-1]
            current_price = df['close'].iloc[-1]
            sma_20 = df['sma_20'].iloc[-1]
            
            signal = None
            confidence = 0.5
            
            # Enhanced RSI levels with trend confirmation
            if current_rsi < 25 and current_price > sma_20:
                signal = 'BUY'
                confidence = 0.7 + (25 - current_rsi) / 100
            elif current_rsi > 75 and current_price < sma_20:
                signal = 'SELL'
                confidence = 0.7 + (current_rsi - 75) / 100
            
            # RSI momentum
            if signal:
                rsi_momentum = current_rsi - rsi_ma
                if (signal == 'BUY' and rsi_momentum > 0) or (signal == 'SELL' and rsi_momentum < 0):
                    confidence += 0.05
            
            if signal and confidence >= self.min_confidence:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': 'Enhanced_RSI',
                    'details': f'RSI: {current_rsi:.1f} Momentum: {rsi_momentum:.1f}'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Enhanced RSI Strategy Error: {e}")
            return None
    
    def _bollinger_momentum_strategy(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Enhanced Bollinger Bands + Momentum"""
        try:
            if len(df) < 30:
                return None
            
            current_price = df['close'].iloc[-1]
            bb_upper = df['bb_upper'].iloc[-1]
            bb_lower = df['bb_lower'].iloc[-1]
            bb_middle = df['bb_middle'].iloc[-1]
            
            # Band position
            band_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            
            # Price momentum
            price_change = (current_price - df['close'].iloc[-5]) / df['close'].iloc[-5]
            
            signal = None
            confidence = 0.5
            
            # Bollinger bounce strategy
            if band_position <= 0.1 and price_change > -0.005:  # Near lower band, momentum turning
                signal = 'BUY'
                confidence = 0.65 + (0.1 - band_position) * 2
            elif band_position >= 0.9 and price_change < 0.005:  # Near upper band, momentum turning
                signal = 'SELL'
                confidence = 0.65 + (band_position - 0.9) * 2
            
            if signal and confidence >= self.min_confidence:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': 'Enhanced_Bollinger_Momentum',
                    'details': f'Band Pos: {band_position:.2f} Momentum: {price_change:.4f}'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Bollinger Momentum Strategy Error: {e}")
            return None
    
    def _trend_following_strategy(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Enhanced Trend Following Strategy"""
        try:
            if len(df) < 50:
                return None
            
            sma_20 = df['sma_20'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            current_price = df['close'].iloc[-1]
            atr = df['atr'].iloc[-1]
            
            # Trend strength
            trend_strength = abs(sma_20 - sma_50) / atr if atr > 0 else 0
            
            signal = None
            confidence = 0.5
            
            # Strong trend continuation
            if sma_20 > sma_50 * 1.001 and current_price > sma_20 and trend_strength > 1.5:
                signal = 'BUY'
                confidence = 0.6 + min(trend_strength / 10, 0.2)
            elif sma_20 < sma_50 * 0.999 and current_price < sma_20 and trend_strength > 1.5:
                signal = 'SELL'
                confidence = 0.6 + min(trend_strength / 10, 0.2)
            
            if signal and confidence >= self.min_confidence:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': 'Enhanced_Trend_Following',
                    'details': f'Trend Strength: {trend_strength:.2f}'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Trend Following Strategy Error: {e}")
            return None
    
    def _multi_timeframe_strategy(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Multi-Timeframe Context Strategy"""
        try:
            if len(df) < 50:
                return None
            
            # Short-term trend (last 10 periods)
            short_trend = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
            
            # Medium-term trend (last 30 periods)
            medium_trend = (df['close'].iloc[-1] - df['close'].iloc[-30]) / df['close'].iloc[-30]
            
            # RSI for momentum
            current_rsi = df['rsi'].iloc[-1]
            
            signal = None
            confidence = 0.5
            
            # Aligned trends
            if short_trend > 0.002 and medium_trend > 0.005 and 30 <= current_rsi <= 60:
                signal = 'BUY'
                confidence = 0.6 + min(medium_trend * 10, 0.2)
            elif short_trend < -0.002 and medium_trend < -0.005 and 40 <= current_rsi <= 70:
                signal = 'SELL'
                confidence = 0.6 + min(abs(medium_trend) * 10, 0.2)
            
            if signal and confidence >= self.min_confidence:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': 'Enhanced_Multi_Timeframe',
                    'details': f'Short: {short_trend:.3f} Medium: {medium_trend:.3f}'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Multi Timeframe Strategy Error: {e}")
            return None
    
    def _build_forex_consensus(self, signals: List[Dict]) -> Optional[Dict]:
        """Build Consensus from Multiple Signals"""
        try:
            if not signals:
                return None
            
            buy_signals = [s for s in signals if s.get('action') == 'BUY']
            sell_signals = [s for s in signals if s.get('action') == 'SELL']
            
            buy_confidence = sum(s.get('confidence', 0) for s in buy_signals)
            sell_confidence = sum(s.get('confidence', 0) for s in sell_signals)
            
            if buy_confidence > sell_confidence and buy_confidence >= 1.2:
                action = 'BUY'
                final_confidence = min(buy_confidence / len(buy_signals), 0.9)
            elif sell_confidence > buy_confidence and sell_confidence >= 1.2:
                action = 'SELL'
                final_confidence = min(sell_confidence / len(sell_signals), 0.9)
            else:
                return None
            
            strategy_names = [s.get('strategy', '') for s in signals]
            
            return {
                'action': action,
                'confidence': final_confidence,
                'strategy': 'Enhanced_Consensus',
                'details': f'Consensus from: {", ".join(strategy_names)}'
            }
            
        except Exception as e:
            logging.error(f"Forex Consensus Error: {e}")
            return None
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI Calculation"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception:
            return pd.Series([50] * len(prices), index=prices.index)
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict:
        """Bollinger Bands Calculation"""
        try:
            middle = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            return {'upper': upper, 'middle': middle, 'lower': lower}
        except Exception:
            return {'upper': prices, 'middle': prices, 'lower': prices}
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR Calculation"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            prev_close = close.shift(1)
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            return atr
        except Exception:
            return pd.Series([0.001] * len(df), index=df.index)

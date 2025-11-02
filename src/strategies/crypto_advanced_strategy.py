#!/usr/bin/env python3
"""
Advanced Multi-Crypto 24/7 Trading Strategy
Speziell für Nacht-Trading und Off-Market-Hours
- Crypto-spezifische Indikatoren
- 24/7 Market Sentiment Analysis  
- Bitcoin Dominance Integration
- Cross-Crypto Correlation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging


class CryptoAdvancedStrategy:
    """Advanced 24/7 Crypto Trading Strategy"""
    
    def __init__(self):
        self.name = "CryptoAdvanced24/7"
        
        # Crypto-spezifische Parameter
        self.volatility_threshold = 0.02  # 2% für Crypto
        self.correlation_window = 20
        self.dominance_threshold = 0.1
        
        # 24/7 Market Sessions
        self.market_sessions = {
            'asian': (0, 8),      # 00:00-08:00 UTC
            'european': (8, 16),  # 08:00-16:00 UTC  
            'american': (16, 24)  # 16:00-24:00 UTC
        }
        
        logging.info("CryptoAdvancedStrategy initialisiert")
    
    def generate_crypto_signals(self, symbol: str, df: pd.DataFrame, market_data: Dict = None) -> List[Dict]:
        """Generiert Crypto-spezifische Signale für 24/7 Trading"""
        
        try:
            if df is None or len(df) < 50:
                return []
            
            # Crypto Market Context
            current_hour = datetime.now().hour
            market_session = self._get_market_session(current_hour)
            
            signals = []
            
            # 1. Advanced RSI mit Crypto-Anpassung
            rsi_signal = self._crypto_rsi_analysis(df, symbol, market_session)
            if rsi_signal:
                signals.append(rsi_signal)
            
            # 2. Crypto MACD mit Volatility Filter
            macd_signal = self._crypto_macd_analysis(df, symbol, market_session)
            if macd_signal:
                signals.append(macd_signal)
            
            # 3. Bollinger Bands mit Crypto-Volatilität
            bb_signal = self._crypto_bollinger_analysis(df, symbol, market_session)
            if bb_signal:
                signals.append(bb_signal)
            
            # 4. 24/7 Volume Momentum
            volume_signal = self._crypto_volume_momentum(df, symbol, market_session)
            if volume_signal:
                signals.append(volume_signal)
            
            # 5. Crypto Fear & Greed Simulation
            sentiment_signal = self._crypto_sentiment_analysis(df, symbol, market_session)
            if sentiment_signal:
                signals.append(sentiment_signal)
            
            # Consensus Building für Crypto
            if len(signals) >= 2:
                consensus = self._build_crypto_consensus(signals, symbol, market_session)
                if consensus:
                    return [consensus]
            
            # Return best individual signal
            if signals:
                best_signal = max(signals, key=lambda x: x.get('confidence', 0))
                if best_signal.get('confidence', 0) >= 0.55:  # Lowered for crypto
                    return [best_signal]
            
            return []
            
        except Exception as e:
            logging.error(f"Crypto Signal Generation Error {symbol}: {e}")
            return []
    
    def _get_market_session(self, hour: int) -> str:
        """Bestimmt aktuelle Marktsession"""
        for session, (start, end) in self.market_sessions.items():
            if start <= hour < end:
                return session
        return 'asian'  # Fallback
    
    def _crypto_rsi_analysis(self, df: pd.DataFrame, symbol: str, session: str) -> Optional[Dict]:
        """Crypto-angepasste RSI Analyse"""
        try:
            # Shorter periods für Crypto
            rsi_short = self._calculate_rsi(df['close'], period=7)
            rsi_long = self._calculate_rsi(df['close'], period=21)
            
            if rsi_short is None or rsi_long is None:
                return None
            
            current_rsi_short = rsi_short.iloc[-1]
            current_rsi_long = rsi_long.iloc[-1]
            
            # Session-angepasste Thresholds
            if session == 'asian':
                oversold, overbought = 25, 75  # Weniger aggressiv
            elif session == 'european':  
                oversold, overbought = 30, 70  # Standard
            else:  # american
                oversold, overbought = 35, 65  # Konservativer
            
            signal = None
            confidence = 0.5
            
            # Enhanced RSI Logic
            if current_rsi_short < oversold and current_rsi_long < 50:
                signal = 'BUY'
                confidence = 0.6 + (oversold - current_rsi_short) / 100
            elif current_rsi_short > overbought and current_rsi_long > 50:
                signal = 'SELL'
                confidence = 0.6 + (current_rsi_short - overbought) / 100
            
            # RSI Divergence Check
            if signal:
                price_trend = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
                rsi_trend = (current_rsi_short - rsi_short.iloc[-5]) / rsi_short.iloc[-5]
                
                # Bullish Divergence
                if price_trend < 0 and rsi_trend > 0 and signal == 'BUY':
                    confidence += 0.1
                # Bearish Divergence  
                elif price_trend > 0 and rsi_trend < 0 and signal == 'SELL':
                    confidence += 0.1
            
            if signal and confidence >= 0.55:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': f'CryptoRSI_{session}',
                    'details': f'RSI: {current_rsi_short:.1f}/{current_rsi_long:.1f}'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Crypto RSI Analysis Error: {e}")
            return None
    
    def _crypto_macd_analysis(self, df: pd.DataFrame, symbol: str, session: str) -> Optional[Dict]:
        """Crypto-optimierte MACD Analyse"""
        try:
            # Crypto-angepasste Perioden
            if 'BTC' in symbol:
                fast, slow, signal_period = 8, 21, 5  # Aggressiver für BTC
            else:
                fast, slow, signal_period = 12, 26, 9  # Standard für Altcoins
            
            macd_line, signal_line, histogram = self._calculate_macd(df['close'], fast, slow, signal_period)
            
            if macd_line is None or signal_line is None:
                return None
            
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_hist = histogram.iloc[-1]
            prev_hist = histogram.iloc[-2]
            
            signal = None
            confidence = 0.5
            
            # MACD Signal Logic
            if current_macd > current_signal and prev_hist < 0 and current_hist > 0:
                signal = 'BUY'
                confidence = 0.65
            elif current_macd < current_signal and prev_hist > 0 and current_hist < 0:
                signal = 'SELL'
                confidence = 0.65
            
            # Session-based confidence adjustment
            if session == 'asian' and signal:
                confidence -= 0.05  # Weniger confident während Asian Session
            elif session == 'american' and signal:
                confidence += 0.05  # Mehr confident während US Session
            
            # Zero Line Cross
            if signal:
                if signal == 'BUY' and current_macd > 0:
                    confidence += 0.1
                elif signal == 'SELL' and current_macd < 0:
                    confidence += 0.1
            
            if signal and confidence >= 0.55:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': f'CryptoMACD_{session}',
                    'details': f'MACD: {current_macd:.6f} Signal: {current_signal:.6f}'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Crypto MACD Analysis Error: {e}")
            return None
    
    def _crypto_bollinger_analysis(self, df: pd.DataFrame, symbol: str, session: str) -> Optional[Dict]:
        """Crypto Bollinger Bands mit hoher Volatilität"""
        try:
            # Crypto-angepasste Parameter
            period = 15  # Shorter for crypto volatility
            std_multiplier = 2.5 if 'BTC' in symbol else 2.0
            
            sma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            
            upper_band = sma + (std * std_multiplier)
            lower_band = sma - (std * std_multiplier)
            
            if sma is None or std is None:
                return None
            
            current_price = df['close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            current_sma = sma.iloc[-1]
            
            # Band Position
            band_position = (current_price - current_lower) / (current_upper - current_lower)
            
            signal = None
            confidence = 0.5
            
            # Bollinger Band Signals
            if band_position <= 0.05:  # Near lower band
                signal = 'BUY'
                confidence = 0.6 + (0.05 - band_position) * 2
            elif band_position >= 0.95:  # Near upper band
                signal = 'SELL' 
                confidence = 0.6 + (band_position - 0.95) * 2
            
            # Band Squeeze Detection
            band_width = (current_upper - current_lower) / current_sma
            avg_band_width = ((upper_band - lower_band) / sma).rolling(window=20).mean().iloc[-1]
            
            if band_width < avg_band_width * 0.8:  # Squeeze
                if signal:
                    confidence += 0.1  # Higher confidence during squeeze
            
            # Volatility Adjustment
            volatility = std.iloc[-1] / current_sma
            if volatility > self.volatility_threshold and signal:
                confidence += 0.05  # Crypto loves volatility
            
            if signal and confidence >= 0.55:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': f'CryptoBB_{session}',
                    'details': f'BB Position: {band_position:.2f} Volatility: {volatility:.3f}'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Crypto Bollinger Analysis Error: {e}")
            return None
    
    def _crypto_volume_momentum(self, df: pd.DataFrame, symbol: str, session: str) -> Optional[Dict]:
        """24/7 Volume Momentum für Crypto"""
        try:
            if 'volume' not in df.columns:
                return None
            
            # Volume-based indicators
            volume_sma = df['volume'].rolling(window=20).mean()
            current_volume = df['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            # Price momentum
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            signal = None
            confidence = 0.5
            
            # Volume Momentum Logic
            if price_change > 0.01 and volume_ratio > 1.5:  # 1% price + high volume
                signal = 'BUY'
                confidence = 0.6 + min(price_change * 5, 0.2) + min((volume_ratio - 1.5) * 0.1, 0.1)
            elif price_change < -0.01 and volume_ratio > 1.5:  # -1% price + high volume
                signal = 'SELL'
                confidence = 0.6 + min(abs(price_change) * 5, 0.2) + min((volume_ratio - 1.5) * 0.1, 0.1)
            
            # Session-based volume patterns
            if session == 'asian' and signal:
                # Asian session typically lower volume
                confidence -= 0.05
            elif session == 'american' and signal:
                # US session higher activity
                confidence += 0.05
            
            if signal and confidence >= 0.55:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': f'CryptoVolume_{session}',
                    'details': f'Price: {price_change:.3f} Volume: {volume_ratio:.1f}x'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Crypto Volume Momentum Error: {e}")
            return None
    
    def _crypto_sentiment_analysis(self, df: pd.DataFrame, symbol: str, session: str) -> Optional[Dict]:
        """Simuliert Crypto Fear & Greed Index"""
        try:
            # Simulated sentiment based on price action
            recent_returns = df['close'].pct_change().tail(10)
            volatility = recent_returns.std()
            momentum = recent_returns.mean()
            
            # Sentiment Score (0-100)
            sentiment_score = 50  # Neutral base
            
            # Price momentum influence
            if momentum > 0:
                sentiment_score += min(momentum * 1000, 30)  # Max +30
            else:
                sentiment_score -= min(abs(momentum) * 1000, 30)  # Max -30
            
            # Volatility influence (high vol = fear)
            vol_impact = min(volatility * 500, 20)
            sentiment_score -= vol_impact
            
            # Ensure bounds
            sentiment_score = max(0, min(100, sentiment_score))
            
            signal = None
            confidence = 0.5
            
            # Sentiment-based signals
            if sentiment_score <= 25:  # Extreme Fear
                signal = 'BUY'
                confidence = 0.65 + (25 - sentiment_score) / 100
            elif sentiment_score >= 75:  # Extreme Greed
                signal = 'SELL'
                confidence = 0.65 + (sentiment_score - 75) / 100
            
            # Session adjustment
            if session == 'asian' and signal:
                confidence -= 0.05  # Less confident in Asian session
            
            if signal and confidence >= 0.55:
                return {
                    'action': signal,
                    'confidence': min(confidence, 0.9),
                    'strategy': f'CryptoSentiment_{session}',
                    'details': f'Sentiment: {sentiment_score:.0f}/100'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Crypto Sentiment Analysis Error: {e}")
            return None
    
    def _build_crypto_consensus(self, signals: List[Dict], symbol: str, session: str) -> Optional[Dict]:
        """Baut Consensus aus mehreren Crypto-Signalen"""
        try:
            if not signals:
                return None
            
            buy_signals = [s for s in signals if s.get('action') == 'BUY']
            sell_signals = [s for s in signals if s.get('action') == 'SELL']
            
            buy_confidence = sum(s.get('confidence', 0) for s in buy_signals)
            sell_confidence = sum(s.get('confidence', 0) for s in sell_signals)
            
            # Crypto consensus needs stronger agreement
            min_consensus_threshold = 1.3  # Higher than traditional forex
            
            if buy_confidence > sell_confidence and buy_confidence >= min_consensus_threshold:
                action = 'BUY'
                final_confidence = min(buy_confidence / len(buy_signals), 0.9)
            elif sell_confidence > buy_confidence and sell_confidence >= min_consensus_threshold:
                action = 'SELL'
                final_confidence = min(sell_confidence / len(sell_signals), 0.9)
            else:
                return None
            
            # Session boost
            if session == 'american':
                final_confidence += 0.05  # US session boost
            
            strategy_names = [s.get('strategy', '') for s in signals]
            
            return {
                'action': action,
                'confidence': min(final_confidence, 0.9),
                'strategy': f'CryptoConsensus_{session}',
                'details': f'Consensus from: {", ".join(strategy_names)}'
            }
            
        except Exception as e:
            logging.error(f"Crypto Consensus Building Error: {e}")
            return None
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[pd.Series]:
        """Berechnet RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception:
            return None
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Optional[pd.Series], Optional[pd.Series], Optional[pd.Series]]:
        """Berechnet MACD"""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            histogram = macd_line - signal_line
            return macd_line, signal_line, histogram
        except Exception:
            return None, None, None


# Integration in StrategyManager
class EnhancedStrategyManager:
    """Enhanced Strategy Manager mit Crypto 24/7 Support"""
    
    def __init__(self):
        self.traditional_strategies = ['macd_rsi', 'bollinger_momentum', 'trend_following']
        self.crypto_strategy = CryptoAdvancedStrategy()
        logging.info("Enhanced StrategyManager mit Crypto-Support initialisiert")
    
    def generate_signals(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """Enhanced Signal Generation mit Crypto-Detection"""
        try:
            # Check if crypto symbol
            crypto_symbols = ['BTC', 'ETH', 'LTC', 'XRP', 'ADA', 'DOT', 'USDT', 'USD']
            is_crypto = any(crypto in symbol.upper() for crypto in crypto_symbols)
            
            if is_crypto:
                # Use advanced crypto strategy
                return self.crypto_strategy.generate_crypto_signals(symbol, df)
            else:
                # Use traditional forex strategies
                return self._generate_traditional_signals(symbol, df)
                
        except Exception as e:
            logging.error(f"Enhanced Signal Generation Error: {e}")
            return []
    
    def _generate_traditional_signals(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """Traditional Forex Signal Generation"""
        # Existing implementation (simplified here)
        signals = []
        
        try:
            # MACD + RSI Strategy
            macd_rsi_signal = self._macd_rsi_strategy(symbol, df)
            if macd_rsi_signal:
                signals.append(macd_rsi_signal)
            
            # Return best signal
            if signals:
                return [max(signals, key=lambda x: x.get('confidence', 0))]
            
        except Exception as e:
            logging.error(f"Traditional Signal Error: {e}")
        
        return []
    
    def _macd_rsi_strategy(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """Traditional MACD + RSI Strategy"""
        try:
            # Simplified implementation
            rsi = self._calculate_rsi(df['close'])
            if rsi is None:
                return None
            
            current_rsi = rsi.iloc[-1]
            
            if current_rsi < 30:
                return {
                    'action': 'BUY',
                    'confidence': 0.6,
                    'strategy': 'MACD_RSI_Traditional'
                }
            elif current_rsi > 70:
                return {
                    'action': 'SELL', 
                    'confidence': 0.6,
                    'strategy': 'MACD_RSI_Traditional'
                }
            
            return None
            
        except Exception:
            return None
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[pd.Series]:
        """RSI Calculation"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception:
            return None

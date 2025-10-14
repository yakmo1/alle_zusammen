#!/usr/bin/env python3
"""
Enhanced Market Session Management für MetaTrader 5
Speziell optimiert für 24/7 Crypto + Enhanced Forex Trading
- Intelligente Session-Erkennung
- Volatilitäts-Tracking
- Symbol-Prioritäts-System
"""

from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
import logging


class AdvancedSessionManager:
    """Advanced Market Session Manager für Enhanced Trading"""
    
    def __init__(self):
        # Enhanced Forex Sessions (UTC)
        self.forex_sessions = {
            'sydney': {
                'start': 21, 'end': 6, 'volatility': 0.7, 
                'symbols': ['AUDUSD', 'NZDUSD', 'AUDNZD'],
                'peak_hours': [22, 23, 0, 1]
            },
            'tokyo': {
                'start': 23, 'end': 8, 'volatility': 0.8, 
                'symbols': ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY'],
                'peak_hours': [1, 2, 3, 4]
            },
            'london': {
                'start': 7, 'end': 16, 'volatility': 1.0, 
                'symbols': ['EURUSD', 'GBPUSD', 'EURGBP', 'EURCHF'],
                'peak_hours': [8, 9, 10, 11]
            },
            'new_york': {
                'start': 12, 'end': 21, 'volatility': 1.0, 
                'symbols': ['EURUSD', 'GBPUSD', 'USDCAD', 'USDCHF'],
                'peak_hours': [13, 14, 15, 16]
            }
        }
        
        # Enhanced Crypto patterns
        self.crypto_patterns = {
            'asian_quiet': {'hours': list(range(0, 4)), 'activity': 0.6, 'volatility': 0.7},
            'asian_active': {'hours': list(range(4, 8)), 'activity': 0.8, 'volatility': 0.9},
            'european_buildup': {'hours': list(range(8, 12)), 'activity': 0.7, 'volatility': 0.8},
            'european_active': {'hours': list(range(12, 16)), 'activity': 0.9, 'volatility': 1.0},
            'american_prime': {'hours': list(range(16, 20)), 'activity': 1.0, 'volatility': 1.1},
            'american_late': {'hours': list(range(20, 24)), 'activity': 0.8, 'volatility': 0.9}
        }
        
        # Session overlaps (enhanced volatility)
        self.overlaps = {
            'london_new_york': {'start': 12, 'end': 16, 'boost': 1.4, 'name': 'EU-US Prime'},
            'sydney_tokyo': {'start': 23, 'end': 6, 'boost': 1.2, 'name': 'Asia Overlap'},
            'tokyo_london': {'start': 7, 'end': 8, 'boost': 1.1, 'name': 'Asia-EU Bridge'}
        }
        
        logging.info("AdvancedSessionManager initialisiert")
    
    def get_enhanced_session_info(self) -> Dict:
        """Enhanced Session Information"""
        try:
            current_hour = datetime.now(timezone.utc).hour
            
            session_info = {
                'current_hour_utc': current_hour,
                'active_forex_sessions': [],
                'crypto_pattern': self._get_crypto_pattern(current_hour),
                'volatility_multiplier': 1.0,
                'recommended_symbols': [],
                'trading_intensity': 'medium',
                'session_overlaps': [],
                'is_peak_time': False
            }
            
            # Analyze active forex sessions
            for session_name, session_data in self.forex_sessions.items():
                if self._is_session_active(current_hour, session_data['start'], session_data['end']):
                    session_info['active_forex_sessions'].append(session_name)
                    session_info['recommended_symbols'].extend(session_data['symbols'])
                    session_info['volatility_multiplier'] *= session_data['volatility']
                    
                    # Check if it's peak time for this session
                    if current_hour in session_data['peak_hours']:
                        session_info['is_peak_time'] = True
            
            # Check for session overlaps
            for overlap_name, overlap_data in self.overlaps.items():
                if self._is_session_active(current_hour, overlap_data['start'], overlap_data['end']):
                    session_info['session_overlaps'].append(overlap_data['name'])
                    session_info['volatility_multiplier'] *= overlap_data['boost']
            
            # Calculate trading intensity
            session_info['trading_intensity'] = self._calculate_enhanced_intensity(session_info)
            
            # Remove duplicate symbols
            session_info['recommended_symbols'] = list(set(session_info['recommended_symbols']))
            
            return session_info
            
        except Exception as e:
            logging.error(f"Enhanced Session Info Error: {e}")
            return self._get_fallback_session_info()
    
    def get_smart_symbol_priorities(self, current_hour: Optional[int] = None) -> List[Tuple[str, float]]:
        """Smart Symbol Selection mit Enhanced Prioritäten"""
        try:
            if current_hour is None:
                current_hour = datetime.now(timezone.utc).hour
            
            symbol_priorities = []
            
            # Enhanced Forex Analysis
            for session_name, session_data in self.forex_sessions.items():
                if self._is_session_active(current_hour, session_data['start'], session_data['end']):
                    base_volatility = session_data['volatility']
                    
                    # Peak time boost
                    peak_boost = 1.2 if current_hour in session_data['peak_hours'] else 1.0
                    
                    # Session overlap boost
                    overlap_boost = self._get_overlap_multiplier(current_hour)
                    
                    for symbol in session_data['symbols']:
                        priority = base_volatility * peak_boost * overlap_boost
                        symbol_priorities.append((symbol, priority))
            
            # Enhanced Crypto Analysis
            crypto_pattern_name = self._get_crypto_pattern(current_hour)
            if crypto_pattern_name in self.crypto_patterns:
                pattern = self.crypto_patterns[crypto_pattern_name]
                crypto_activity = pattern['activity']
                crypto_volatility = pattern['volatility']
                
                # Weekend boost for crypto (when forex is less active)
                weekend_boost = 1.3 if datetime.now().weekday() >= 5 else 1.0
                
                crypto_symbols = [
                    ('BTCUSD', 0.95),
                    ('ETHUSD', 0.90),
                    ('LTCUSD', 0.80),
                    ('XRPUSD', 0.75),
                    ('ADAUSD', 0.70),
                    ('DOTUSD', 0.70),
                    ('AVAXUSD', 0.65),
                    ('SOLUSD', 0.65)
                ]
                
                for symbol, base_priority in crypto_symbols:
                    enhanced_priority = (base_priority * crypto_activity * 
                                       crypto_volatility * weekend_boost)
                    symbol_priorities.append((symbol, enhanced_priority))
            
            # Sort by priority and return top 12
            symbol_priorities.sort(key=lambda x: x[1], reverse=True)
            return symbol_priorities[:12]
            
        except Exception as e:
            logging.error(f"Smart Symbol Priorities Error: {e}")
            return [('EURUSD', 0.8), ('BTCUSD', 0.9), ('GBPUSD', 0.7)]
    
    def get_enhanced_trading_parameters(self) -> Dict:
        """Enhanced Trading Parameters basierend auf Session"""
        try:
            session_info = self.get_enhanced_session_info()
            
            # Base parameters
            parameters = {
                'confidence_threshold': 0.55,
                'max_trades_per_hour': 3,
                'max_daily_trades': 10,
                'risk_multiplier': 1.0,
                'position_size_multiplier': 1.0,
                'signal_sensitivity': 1.0,
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.0
            }
            
            # Intensity-based adjustments
            intensity = session_info['trading_intensity']
            volatility = session_info['volatility_multiplier']
            
            if intensity == 'high':
                parameters.update({
                    'confidence_threshold': 0.50,  # More aggressive
                    'max_trades_per_hour': 5,
                    'max_daily_trades': 15,
                    'signal_sensitivity': 1.3,
                    'risk_multiplier': 1.1
                })
            elif intensity == 'very_high':
                parameters.update({
                    'confidence_threshold': 0.45,  # Very aggressive
                    'max_trades_per_hour': 6,
                    'max_daily_trades': 20,
                    'signal_sensitivity': 1.5,
                    'risk_multiplier': 1.2
                })
            elif intensity == 'low':
                parameters.update({
                    'confidence_threshold': 0.65,  # More conservative
                    'max_trades_per_hour': 1,
                    'max_daily_trades': 5,
                    'signal_sensitivity': 0.7,
                    'risk_multiplier': 0.8
                })
            
            # Volatility-based adjustments
            if volatility > 1.5:  # Very high volatility
                parameters['position_size_multiplier'] = 0.7  # Smaller positions
                parameters['stop_loss_multiplier'] = 1.3    # Wider stops
                parameters['confidence_threshold'] += 0.1
            elif volatility > 1.2:  # High volatility
                parameters['position_size_multiplier'] = 0.85
                parameters['stop_loss_multiplier'] = 1.2
                parameters['confidence_threshold'] += 0.05
            elif volatility < 0.8:  # Low volatility
                parameters['position_size_multiplier'] = 1.2
                parameters['stop_loss_multiplier'] = 0.9
                parameters['confidence_threshold'] -= 0.05
            
            # Peak time boost
            if session_info['is_peak_time']:
                parameters['signal_sensitivity'] *= 1.1
                parameters['max_trades_per_hour'] += 1
            
            return parameters
            
        except Exception as e:
            logging.error(f"Enhanced Trading Parameters Error: {e}")
            return self._get_fallback_parameters()
    
    def should_trade_aggressively(self, symbol: str, current_hour: Optional[int] = None) -> bool:
        """Prüft ob aggressives Trading empfohlen wird"""
        try:
            if current_hour is None:
                current_hour = datetime.now(timezone.utc).hour
            
            session_info = self.get_enhanced_session_info()
            
            # High intensity sessions
            if session_info['trading_intensity'] in ['high', 'very_high']:
                return True
            
            # Peak time trading
            if session_info['is_peak_time']:
                return True
            
            # Session overlaps
            if session_info['session_overlaps']:
                return True
            
            # Crypto during high activity periods
            crypto_symbols = ['BTC', 'ETH', 'LTC', 'XRP', 'ADA', 'DOT']
            if any(crypto in symbol.upper() for crypto in crypto_symbols):
                crypto_pattern = session_info['crypto_pattern']
                if crypto_pattern in ['american_prime', 'european_active']:
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"Should Trade Aggressively Error: {e}")
            return False
    
    def get_session_summary(self) -> str:
        """Detailed Session Summary für Logging"""
        try:
            session_info = self.get_enhanced_session_info()
            parameters = self.get_enhanced_trading_parameters()
            top_symbols = self.get_smart_symbol_priorities()[:5]
            
            summary = []
            summary.append(f"🕐 SESSION {session_info['current_hour_utc']:02d}:00 UTC")
            summary.append(f"📊 Forex: {', '.join(session_info['active_forex_sessions']) or 'Closed'}")
            summary.append(f"₿ Crypto: {session_info['crypto_pattern']}")
            summary.append(f"⚡ Intensity: {session_info['trading_intensity'].upper()}")
            summary.append(f"📈 Volatility: {session_info['volatility_multiplier']:.1f}x")
            
            if session_info['session_overlaps']:
                summary.append(f"🔄 Overlaps: {', '.join(session_info['session_overlaps'])}")
            
            if session_info['is_peak_time']:
                summary.append("🎯 PEAK TIME")
            
            summary.append(f"🎲 Confidence: {parameters['confidence_threshold']:.0%}")
            summary.append(f"🔝 Top: {', '.join([s[0] for s in top_symbols])}")
            
            return " | ".join(summary)
            
        except Exception as e:
            logging.error(f"Session Summary Error: {e}")
            return "SESSION INFO UNAVAILABLE"
    
    def _is_session_active(self, current_hour: int, start_hour: int, end_hour: int) -> bool:
        """Session Activity Check (handles midnight crossover)"""
        if start_hour <= end_hour:
            return start_hour <= current_hour <= end_hour
        else:  # Crosses midnight
            return current_hour >= start_hour or current_hour <= end_hour
    
    def _get_crypto_pattern(self, current_hour: int) -> str:
        """Current Crypto Activity Pattern"""
        for pattern_name, pattern_data in self.crypto_patterns.items():
            if current_hour in pattern_data['hours']:
                return pattern_name
        return 'american_late'  # Fallback
    
    def _get_overlap_multiplier(self, current_hour: int) -> float:
        """Calculate Session Overlap Multiplier"""
        total_boost = 1.0
        for overlap_data in self.overlaps.values():
            if self._is_session_active(current_hour, overlap_data['start'], overlap_data['end']):
                total_boost *= overlap_data['boost']
        return total_boost
    
    def _calculate_enhanced_intensity(self, session_info: Dict) -> str:
        """Calculate Enhanced Trading Intensity"""
        try:
            score = 0
            
            # Active sessions
            score += len(session_info['active_forex_sessions']) * 2
            
            # Session overlaps
            score += len(session_info['session_overlaps']) * 3
            
            # Peak time
            if session_info['is_peak_time']:
                score += 3
            
            # Volatility
            if session_info['volatility_multiplier'] > 1.3:
                score += 4
            elif session_info['volatility_multiplier'] > 1.1:
                score += 2
            
            # Crypto activity
            crypto_pattern = session_info['crypto_pattern']
            if crypto_pattern in ['american_prime', 'european_active']:
                score += 2
            elif crypto_pattern in ['american_late', 'asian_active']:
                score += 1
            
            # Determine intensity
            if score >= 10:
                return 'very_high'
            elif score >= 6:
                return 'high'
            elif score >= 3:
                return 'medium'
            else:
                return 'low'
                
        except Exception:
            return 'medium'
    
    def _get_fallback_session_info(self) -> Dict:
        """Fallback Session Info"""
        return {
            'current_hour_utc': datetime.now(timezone.utc).hour,
            'active_forex_sessions': ['london'],
            'crypto_pattern': 'european_active',
            'volatility_multiplier': 1.0,
            'recommended_symbols': ['EURUSD', 'BTCUSD'],
            'trading_intensity': 'medium',
            'session_overlaps': [],
            'is_peak_time': False
        }
    
    def _get_fallback_parameters(self) -> Dict:
        """Fallback Trading Parameters"""
        return {
            'confidence_threshold': 0.55,
            'max_trades_per_hour': 3,
            'max_daily_trades': 10,
            'risk_multiplier': 1.0,
            'position_size_multiplier': 1.0,
            'signal_sensitivity': 1.0,
            'stop_loss_multiplier': 1.0,
            'take_profit_multiplier': 1.0
        }

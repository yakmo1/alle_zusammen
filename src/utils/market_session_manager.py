#!/usr/bin/env python3
"""
MT5 Auto-Start und Market Session Manager
Verwaltet MetaTrader 5 Start/Stop und überwacht Handelszeiten
"""

import os
import sys
import subprocess
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import pytz

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class MarketSessionManager:
    """Verwaltet Handelszeiten für verschiedene Märkte und Symbole"""
    
    def __init__(self):
        self.market_sessions = {
            # Forex Markets (24/5 aber mit unterschiedlichen Liquiditätszeiten)
            'FOREX': {
                'EURUSD': {'type': 'forex', 'high_liquidity_hours': [(8, 17), (13, 22)]},  # London + NY Overlap
                'GBPUSD': {'type': 'forex', 'high_liquidity_hours': [(8, 17), (13, 22)]},
                'USDJPY': {'type': 'forex', 'high_liquidity_hours': [(0, 9), (13, 22)]},   # Tokyo + NY
                'AUDUSD': {'type': 'forex', 'high_liquidity_hours': [(22, 7), (13, 16)]}, # Sydney + NY
                'USDCAD': {'type': 'forex', 'high_liquidity_hours': [(13, 22)]},          # NY Session
                'NZDUSD': {'type': 'forex', 'high_liquidity_hours': [(22, 6)]},           # Wellington/Sydney
                'EURGBP': {'type': 'forex', 'high_liquidity_hours': [(8, 17)]},           # London
                'EURJPY': {'type': 'forex', 'high_liquidity_hours': [(0, 9), (8, 17)]},  # Tokyo + London
            },
            
            # Indices (begrenzte Handelszeiten)
            'INDICES': {
                'GER40': {'type': 'index', 'trading_hours': [(8, 22)], 'timezone': 'Europe/Berlin'},
                'US30': {'type': 'index', 'trading_hours': [(9, 16), (18, 23)], 'timezone': 'America/New_York'},
                'SPX500': {'type': 'index', 'trading_hours': [(9, 16), (18, 23)], 'timezone': 'America/New_York'},
                'UK100': {'type': 'index', 'trading_hours': [(8, 16)], 'timezone': 'Europe/London'},
                'JPN225': {'type': 'index', 'trading_hours': [(9, 15)], 'timezone': 'Asia/Tokyo'},
            },
            
            # Commodities
            'COMMODITIES': {
                'GOLD': {'type': 'commodity', 'trading_hours': [(23, 22)], 'timezone': 'UTC'},  # Almost 24/5
                'SILVER': {'type': 'commodity', 'trading_hours': [(23, 22)], 'timezone': 'UTC'},
                'OIL': {'type': 'commodity', 'trading_hours': [(23, 22)], 'timezone': 'UTC'},
                'COPPER': {'type': 'commodity', 'trading_hours': [(23, 22)], 'timezone': 'UTC'},
            },
            
            # Cryptocurrencies (24/7 Trading!)
            'CRYPTO': {
                'BTCUSD': {'type': 'crypto', 'trading_hours': [(0, 24)], 'timezone': 'UTC', 'volatility': 'high'},
                'ETHUSD': {'type': 'crypto', 'trading_hours': [(0, 24)], 'timezone': 'UTC', 'volatility': 'high'},
                'XRPUSD': {'type': 'crypto', 'trading_hours': [(0, 24)], 'timezone': 'UTC', 'volatility': 'very_high'},
                'LTCUSD': {'type': 'crypto', 'trading_hours': [(0, 24)], 'timezone': 'UTC', 'volatility': 'high'},
                'ADAUSD': {'type': 'crypto', 'trading_hours': [(0, 24)], 'timezone': 'UTC', 'volatility': 'very_high'},
                'DOTUSD': {'type': 'crypto', 'trading_hours': [(0, 24)], 'timezone': 'UTC', 'volatility': 'very_high'},
                'LINKUSD': {'type': 'crypto', 'trading_hours': [(0, 24)], 'timezone': 'UTC', 'volatility': 'very_high'},
                'BNBUSD': {'type': 'crypto', 'trading_hours': [(0, 24)], 'timezone': 'UTC', 'volatility': 'high'},
            }
        }
        
        # Weekend Check (Forex: Freitag 22:00 UTC bis Sonntag 22:00 UTC geschlossen)
        self.forex_weekend_break = {
            'close': {'day': 5, 'hour': 22, 'minute': 0},  # Friday 22:00 UTC
            'open': {'day': 0, 'hour': 22, 'minute': 0}    # Sunday 22:00 UTC
        }
    
    def is_market_open(self, symbol: str) -> Tuple[bool, str, float]:
        """
        Prüft ob Markt für Symbol geöffnet ist
        Returns: (is_open, reason, liquidity_score 0-1)
        """
        now_utc = datetime.now(timezone.utc)
        
        # Weekend Check für Forex
        if self._is_forex_weekend(symbol, now_utc):
            return False, "Forex Weekend Break", 0.0
        
        # Finde Symbol in Markets
        symbol_info = self._find_symbol_info(symbol)
        if not symbol_info:
            return True, "Unknown Symbol - Assuming Open", 0.5  # Default für unbekannte Symbole
        
        market_type = symbol_info['type']
        
        if market_type == 'forex':
            return self._check_forex_session(symbol, symbol_info, now_utc)
        elif market_type == 'crypto':
            return self._check_crypto_session(symbol, symbol_info, now_utc)
        elif market_type in ['index', 'commodity']:
            return self._check_limited_hours_session(symbol, symbol_info, now_utc)
        
        return True, "Market Type Unknown", 0.5
    
    def _is_forex_weekend(self, symbol: str, now_utc: datetime) -> bool:
        """Prüft Forex Weekend Break"""
        symbol_info = self._find_symbol_info(symbol)
        if not symbol_info or symbol_info['type'] != 'forex':
            return False
        
        weekday = now_utc.weekday()  # 0=Monday, 6=Sunday
        hour = now_utc.hour
        
        # Freitag nach 22:00 UTC
        if weekday == 4 and hour >= 22:
            return True
        
        # Samstag ganztägig
        if weekday == 5:
            return True
        
        # Sonntag vor 22:00 UTC
        if weekday == 6 and hour < 22:
            return True
        
        return False
    
    def _find_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Findet Symbol-Info in allen Märkten"""
        for market_category in self.market_sessions.values():
            if symbol in market_category:
                return market_category[symbol]
        return None
    
    def _check_forex_session(self, symbol: str, symbol_info: Dict, now_utc: datetime) -> Tuple[bool, str, float]:
        """Prüft Forex-Handelszeiten und Liquidität"""
        hour = now_utc.hour
        
        # Forex ist grundsätzlich 24/5 geöffnet (außer Weekend)
        high_liquidity_hours = symbol_info.get('high_liquidity_hours', [])
        
        # Prüfe High-Liquidity Zeiten
        in_high_liquidity = False
        for start_hour, end_hour in high_liquidity_hours:
            if start_hour <= end_hour:  # Normale Zeitspanne
                if start_hour <= hour < end_hour:
                    in_high_liquidity = True
                    break
            else:  # Über Mitternacht (z.B. 22-7)
                if hour >= start_hour or hour < end_hour:
                    in_high_liquidity = True
                    break
        
        if in_high_liquidity:
            return True, "High Liquidity Session", 1.0
        else:
            return True, "Low Liquidity Session", 0.3
    
    def _check_limited_hours_session(self, symbol: str, symbol_info: Dict, now_utc: datetime) -> Tuple[bool, str, float]:
        """Prüft begrenzte Handelszeiten (Indices, Commodities)"""
        trading_hours = symbol_info.get('trading_hours', [])
        symbol_timezone = symbol_info.get('timezone', 'UTC')
        
        # Konvertiere Zeit zur Symbol-Zeitzone
        tz = pytz.timezone(symbol_timezone)
        local_time = now_utc.astimezone(tz)
        local_hour = local_time.hour
        local_weekday = local_time.weekday()
        
        # Prüfe Wochenende (für die meisten Indices/Commodities)
        if local_weekday >= 5:  # Samstag oder Sonntag
            return False, f"Weekend in {symbol_timezone}", 0.0
        
        # Prüfe Handelszeiten
        for start_hour, end_hour in trading_hours:
            if start_hour <= local_hour < end_hour:
                return True, f"Trading Hours in {symbol_timezone}", 0.8
        
        return False, f"Outside Trading Hours in {symbol_timezone}", 0.0
    
    def _check_crypto_session(self, symbol: str, symbol_info: Dict, now_utc: datetime) -> Tuple[bool, str, float]:
        """Prüft Kryptowährungs-Handelszeiten (24/7)"""
        volatility = symbol_info.get('volatility', 'medium')
        
        # Crypto ist immer geöffnet, aber Liquidität variiert
        hour = now_utc.hour
        
        # High-Volume Zeiten für Crypto (basierend auf US/EU/ASIA Sessions)
        if 12 <= hour <= 22:  # EU + US Sessions
            liquidity_score = 1.0
            reason = "High Volume Session (EU+US)"
        elif 0 <= hour <= 8:  # ASIA Session
            liquidity_score = 0.8
            reason = "Medium Volume Session (ASIA)"
        else:  # Low volume hours
            liquidity_score = 0.6
            reason = "Lower Volume Session"
        
        # Adjust for volatility
        if volatility == 'very_high':
            liquidity_score *= 0.8  # Reduce for very volatile cryptos
        elif volatility == 'high':
            liquidity_score *= 0.9
        
        return True, f"24/7 Crypto - {reason}", liquidity_score

    def get_next_market_open(self, symbol: str) -> Optional[datetime]:
        """Berechnet wann der Markt als nächstes öffnet"""
        # Vereinfachte Implementierung - kann erweitert werden
        now_utc = datetime.now(timezone.utc)
        
        # Für Forex: nächster Sonntag 22:00 UTC wenn Weekend
        symbol_info = self._find_symbol_info(symbol)
        if symbol_info and symbol_info['type'] == 'forex':
            if self._is_forex_weekend(symbol, now_utc):
                # Berechne nächsten Sonntag 22:00 UTC
                days_until_sunday = (6 - now_utc.weekday()) % 7
                if days_until_sunday == 0 and now_utc.hour >= 22:
                    days_until_sunday = 7
                
                next_open = now_utc.replace(hour=22, minute=0, second=0, microsecond=0)
                next_open = next_open.replace(day=now_utc.day + days_until_sunday)
                return next_open
        
        return None


class MT5AutoManager:
    """Automatisches MT5 Start/Stop Management"""
    
    def __init__(self, mt5_path: str, login: str, password: str, server: str):
        self.mt5_path = mt5_path
        self.login = login
        self.password = password
        self.server = server
        self.process = None
        self.session_manager = MarketSessionManager()
        
    def start_mt5_terminal(self) -> bool:
        """Startet MT5 Terminal automatisch"""
        try:
            if self.is_mt5_running():
                logging.info("MT5 Terminal läuft bereits")
                return True
            
            logging.info(f"Starte MT5 Terminal: {self.mt5_path}")
            
            # MT5 Terminal starten
            self.process = subprocess.Popen([
                self.mt5_path,
                f"/login:{self.login}",
                f"/server:{self.server}",
                f"/password:{self.password}",
                "/portable"  # Portable Mode für bessere Kontrolle
            ])
            
            # Warte auf Start
            time.sleep(10)
            
            # Prüfe ob erfolgreich gestartet
            if self.is_mt5_running():
                logging.info("✅ MT5 Terminal erfolgreich gestartet")
                return True
            else:
                logging.error("❌ MT5 Terminal Start fehlgeschlagen")
                return False
                
        except Exception as e:
            logging.error(f"Fehler beim Starten von MT5: {e}")
            return False
    
    def is_mt5_running(self) -> bool:
        """Prüft ob MT5 Terminal läuft"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if 'terminal64.exe' in proc.info['name'].lower():
                    return True
            return False
        except ImportError:
            # Fallback ohne psutil
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq terminal64.exe'], 
                                  capture_output=True, text=True, shell=True)
            return 'terminal64.exe' in result.stdout
    
    def stop_mt5_terminal(self):
        """Stoppt MT5 Terminal"""
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=30)
                logging.info("MT5 Terminal gestoppt")
        except Exception as e:
            logging.error(f"Fehler beim Stoppen von MT5: {e}")
    
    def get_tradeable_symbols(self) -> List[Tuple[str, bool, float]]:
        """
        Gibt Liste aller handelbaren Symbole mit Status zurück
        Returns: List[(symbol, is_open, liquidity_score)]
        """
        symbols = [
            # Major Forex Pairs
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            # Minor Forex Pairs
            'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'EURAUD', 'GBPAUD',
            # Indices
            'GER40', 'US30', 'SPX500', 'UK100', 'JPN225',
            # Commodities
            'GOLD', 'SILVER', 'OIL', 'COPPER',
            # Cryptocurrencies (24/7!)
            'BTCUSD', 'ETHUSD', 'XRPUSD', 'LTCUSD', 'ADAUSD', 'DOTUSD', 'LINKUSD', 'BNBUSD'
        ]
        
        tradeable = []
        for symbol in symbols:
            is_open, reason, liquidity = self.session_manager.is_market_open(symbol)
            tradeable.append((symbol, is_open, liquidity))
            
        return tradeable
    
    def get_optimal_trading_symbols(self, min_liquidity: float = 0.5) -> List[str]:
        """Gibt optimale Trading-Symbole basierend auf aktueller Session zurück"""
        tradeable = self.get_tradeable_symbols()
        optimal = []
        
        for symbol, is_open, liquidity in tradeable:
            if is_open and liquidity >= min_liquidity:
                optimal.append(symbol)
        
        logging.info(f"Optimale Trading-Symbole: {optimal}")
        return optimal


def test_market_sessions():
    """Test der Market Session Detection"""
    print("🕐 Testing Market Session Manager...")
    
    session_manager = MarketSessionManager()
    
    test_symbols = ['EURUSD', 'GBPUSD', 'GER40', 'US30', 'GOLD', 'BTCUSD', 'ETHUSD']
    
    print(f"\n📊 Current Market Status ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}):")
    print("-" * 80)
    
    for symbol in test_symbols:
        is_open, reason, liquidity = session_manager.is_market_open(symbol)
        status = "🟢 OPEN" if is_open else "🔴 CLOSED"
        liquidity_bar = "█" * int(liquidity * 10) + "░" * (10 - int(liquidity * 10))
        
        print(f"{symbol:8} | {status:8} | Liquidity: {liquidity_bar} {liquidity:.1f} | {reason}")


if __name__ == "__main__":
    test_market_sessions()

"""
Risk Management System
Überwacht und kontrolliert Trading-Risiken
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

class RiskManager:
    def __init__(self):
        self.max_daily_loss_percent = 5.0  # Maximaler täglicher Verlust: 5%
        self.max_positions_per_symbol = 2   # Max 2 Positionen pro Symbol
        self.max_total_positions = 10       # Max 10 Positionen gesamt
        self.max_risk_per_trade = 2.0       # Max 2% Risiko pro Trade
        self.max_correlation_exposure = 30.0 # Max 30% in korrelierten Paaren
        
        # Korrelations-Gruppen
        self.correlation_groups = {
            'EUR_pairs': ['EURUSD', 'EURGBP', 'EURJPY', 'EURCHF', 'EURAUD'],
            'USD_pairs': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD'],
            'JPY_pairs': ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CHFJPY'],
            'GBP_pairs': ['GBPUSD', 'EURGBP', 'GBPJPY', 'GBPCHF', 'GBPAUD']
        }
        
        logging.info("Risk Manager initialisiert")
    
    def check_risk_limits(self, account_info: Dict[str, Any], signal: Dict[str, Any]) -> bool:
        """Überprüft alle Risk-Limits vor Trade-Ausführung"""
        try:
            # 1. Täglicher Verlust-Check
            if not self.check_daily_loss_limit(account_info):
                logging.warning("Tägliches Verlust-Limit erreicht")
                return False
            
            # 2. Position-Limits
            if not self.check_position_limits(signal):
                logging.warning("Position-Limits erreicht")
                return False
            
            # 3. Risiko pro Trade
            if not self.check_trade_risk(account_info, signal):
                logging.warning("Trade-Risiko zu hoch")
                return False
            
            # 4. Korrelations-Exposure
            if not self.check_correlation_exposure(account_info, signal):
                logging.warning("Korrelations-Exposure zu hoch")
                return False
            
            # 5. Margin-Check
            if not self.check_margin_requirements(account_info, signal):
                logging.warning("Unzureichende Margin")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Risk-Check: {e}")
            return False
    
    def check_daily_loss_limit(self, account_info: Dict[str, Any]) -> bool:
        """Prüft tägliches Verlust-Limit"""
        try:
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', 0)
            
            if balance <= 0:
                return False
            
            # Täglicher Verlust berechnen
            daily_loss_percent = ((balance - equity) / balance) * 100
            
            if daily_loss_percent >= self.max_daily_loss_percent:
                logging.warning(f"Täglicher Verlust {daily_loss_percent:.2f}% erreicht Limit {self.max_daily_loss_percent}%")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Daily Loss Check: {e}")
            return False
    
    def check_position_limits(self, signal: Dict[str, Any]) -> bool:
        """Prüft Position-Limits"""
        try:
            # Diese Methode sollte mit MT5-Connector die aktuellen Positionen prüfen
            # Für jetzt als Platzhalter implementiert
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Position Limit Check: {e}")
            return False
    
    def check_trade_risk(self, account_info: Dict[str, Any], signal: Dict[str, Any]) -> bool:
        """Prüft Risiko pro Trade"""
        try:
            balance = account_info.get('balance', 0)
            entry_price = signal.get('entry_price', 0)
            stop_loss = signal.get('stop_loss', 0)
            
            if balance <= 0 or entry_price <= 0 or stop_loss <= 0:
                return False
            
            # Risiko pro Unit berechnen
            risk_per_unit = abs(entry_price - stop_loss)
            
            # Maximale Position basierend auf Risiko
            max_risk_amount = balance * (self.max_risk_per_trade / 100)
            max_position_size = max_risk_amount / risk_per_unit
            
            # Confidence-basierte Anpassung
            confidence = signal.get('confidence', 0)
            if confidence < 70:
                max_position_size *= 0.5  # Halbes Risiko bei niedriger Confidence
            
            # Minimum Position Size
            if max_position_size < 0.01:
                logging.warning("Berechnet Position zu klein")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Trade Risk Check: {e}")
            return False
    
    def check_correlation_exposure(self, account_info: Dict[str, Any], signal: Dict[str, Any]) -> bool:
        """Prüft Korrelations-Exposure"""
        try:
            symbol = signal.get('symbol', '')
            
            # Finde Korrelations-Gruppen für das Symbol
            symbol_groups = []
            for group_name, symbols in self.correlation_groups.items():
                if symbol in symbols:
                    symbol_groups.append(group_name)
            
            if not symbol_groups:
                return True  # Keine Korrelations-Beschränkung
            
            # Hier würde normalerweise das aktuelle Exposure berechnet
            # Für jetzt als vereinfachte Implementierung
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Correlation Check: {e}")
            return False
    
    def check_margin_requirements(self, account_info: Dict[str, Any], signal: Dict[str, Any]) -> bool:
        """Prüft Margin-Anforderungen"""
        try:
            free_margin = account_info.get('free_margin', 0)
            margin_level = account_info.get('margin_level', 0)
            
            # Minimum Margin Level: 200%
            if margin_level > 0 and margin_level < 200:
                logging.warning(f"Margin Level zu niedrig: {margin_level}%")
                return False
            
            # Minimum Free Margin: 1000 USD
            if free_margin < 1000:
                logging.warning(f"Free Margin zu niedrig: {free_margin}")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Margin Check: {e}")
            return False
    
    def calculate_position_size(self, account_info: Dict[str, Any], signal: Dict[str, Any]) -> float:
        """Berechnet optimale Positionsgröße unter Berücksichtigung aller Risiko-Faktoren"""
        try:
            balance = account_info.get('balance', 0)
            entry_price = signal.get('entry_price', 0)
            stop_loss = signal.get('stop_loss', 0)
            confidence = signal.get('confidence', 0)
            
            if balance <= 0 or entry_price <= 0 or stop_loss <= 0:
                return 0
            
            # Basis-Risiko berechnen
            risk_per_unit = abs(entry_price - stop_loss)
            base_risk_amount = balance * (self.max_risk_per_trade / 100)
            base_position_size = base_risk_amount / risk_per_unit
            
            # Confidence-Anpassung
            confidence_multiplier = self.get_confidence_multiplier(confidence)
            adjusted_position_size = base_position_size * confidence_multiplier
            
            # Volatilitäts-Anpassung
            volatility_multiplier = self.get_volatility_multiplier(signal)
            final_position_size = adjusted_position_size * volatility_multiplier
            
            # Minimum und Maximum
            min_size = 0.01
            max_size = balance * 0.1 / entry_price  # Max 10% des Kontos
            
            final_position_size = max(min_size, min(final_position_size, max_size))
            
            return round(final_position_size, 2)
            
        except Exception as e:
            logging.error(f"Fehler bei Position Size Berechnung: {e}")
            return 0
    
    def get_confidence_multiplier(self, confidence: float) -> float:
        """Confidence-basierter Multiplikator für Positionsgröße"""
        if confidence >= 90:
            return 1.0
        elif confidence >= 80:
            return 0.8
        elif confidence >= 70:
            return 0.6
        elif confidence >= 60:
            return 0.4
        else:
            return 0.2
    
    def get_volatility_multiplier(self, signal: Dict[str, Any]) -> float:
        """Volatilitäts-basierter Multiplikator"""
        # Vereinfachte Implementierung
        # In einer echten Implementierung würde hier ATR oder andere Volatilitäts-Metriken verwendet
        return 0.8  # Konservative Anpassung
    
    def monitor_open_positions(self, positions: List[Dict[str, Any]], account_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Überwacht offene Positionen und gibt Empfehlungen"""
        recommendations = []
        
        try:
            for position in positions:
                # Gewinn/Verlust prüfen
                profit_percent = (position['profit'] / account_info['balance']) * 100
                
                # Stop-Loss Anpassungen
                if profit_percent > 2:  # 2% Gewinn
                    recommendations.append({
                        'type': 'ADJUST_SL',
                        'ticket': position['ticket'],
                        'reason': 'Gewinn absichern',
                        'new_sl': position['open_price']  # Break-even
                    })
                
                # Position schließen bei großem Verlust
                elif profit_percent < -3:  # 3% Verlust
                    recommendations.append({
                        'type': 'CLOSE_POSITION',
                        'ticket': position['ticket'],
                        'reason': 'Verlust-Limit erreicht'
                    })
                
                # Trailing Stop
                elif profit_percent > 1:
                    recommendations.append({
                        'type': 'TRAILING_STOP',
                        'ticket': position['ticket'],
                        'reason': 'Gewinn mit Trailing Stop sichern'
                    })
            
            return recommendations
            
        except Exception as e:
            logging.error(f"Fehler beim Position Monitoring: {e}")
            return []
    
    def get_risk_report(self, account_info: Dict[str, Any], positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Erstellt einen Risiko-Report"""
        try:
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', 0)
            margin_level = account_info.get('margin_level', 0)
            
            # Gesamtes Risiko berechnen
            total_risk = sum([abs(pos['profit']) for pos in positions if pos['profit'] < 0])
            risk_percent = (total_risk / balance * 100) if balance > 0 else 0
            
            # Exposure nach Währungen
            currency_exposure = {}
            for position in positions:
                symbol = position['symbol']
                base_currency = symbol[:3]
                quote_currency = symbol[3:]
                
                exposure = position['volume'] * position['open_price']
                currency_exposure[base_currency] = currency_exposure.get(base_currency, 0) + exposure
                currency_exposure[quote_currency] = currency_exposure.get(quote_currency, 0) - exposure
            
            return {
                'timestamp': datetime.now().isoformat(),
                'account_balance': balance,
                'account_equity': equity,
                'margin_level': margin_level,
                'total_positions': len(positions),
                'total_risk_amount': total_risk,
                'risk_percent': risk_percent,
                'currency_exposure': currency_exposure,
                'risk_status': self.get_risk_status(risk_percent, margin_level)
            }
            
        except Exception as e:
            logging.error(f"Fehler beim Risk Report: {e}")
            return {'error': str(e)}
    
    def get_risk_status(self, risk_percent: float, margin_level: float) -> str:
        """Bestimmt den Risiko-Status"""
        if risk_percent > 5 or margin_level < 200:
            return 'HIGH_RISK'
        elif risk_percent > 3 or margin_level < 300:
            return 'MEDIUM_RISK'
        else:
            return 'LOW_RISK'

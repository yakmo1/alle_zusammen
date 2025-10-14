#!/usr/bin/env python3
"""
ML Trading Signal Integration
Verbindet die ML-Predictions mit dem Trading-System
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

class MLTradingIntegration:
    """Integriert ML-Predictions in das Trading-System"""
    
    def __init__(self, signal_file="current_trading_signal.json"):
        self.signal_file = signal_file
        self.logger = logging.getLogger(__name__)
        
    def get_ml_signal(self) -> Optional[Dict]:
        """Lädt das aktuelle ML-Trading-Signal"""
        try:
            if os.path.exists(self.signal_file):
                with open(self.signal_file, 'r') as f:
                    signal_data = json.load(f)
                
                # Überprüfe, ob Signal aktuell ist (max 30 Minuten alt)
                signal_time = datetime.strptime(signal_data['timestamp'], '%Y-%m-%d %H:%M:%S')
                if datetime.now() - signal_time < timedelta(minutes=30):
                    return signal_data
                else:
                    self.logger.warning("ML signal is outdated")
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading ML signal: {e}")
            return None
    
    def should_execute_trade(self, symbol="EURUSD") -> Dict[str, any]:
        """
        Entscheidet basierend auf ML-Signal, ob ein Trade ausgeführt werden soll
        
        Returns:
            Dict mit trade_action, confidence, reason
        """
        signal = self.get_ml_signal()
        
        if not signal:
            return {
                "trade_action": "HOLD",
                "confidence": 0,
                "reason": "No current ML signal available"
            }
        
        action = signal['action'].upper()
        confidence = signal['confidence']
        
        # Trading-Regeln basierend auf ML-Confidence
        if confidence >= 75:
            strength = "STRONG"
        elif confidence >= 65:
            strength = "MODERATE" 
        else:
            strength = "WEAK"
        
        # Entscheidungslogik
        if action in ['BULLISH', 'BEARISH'] and confidence >= 65:
            trade_action = "BUY" if action == "BULLISH" else "SELL"
            reason = f"{strength} ML signal: {action} ({confidence}%)"
        else:
            trade_action = "HOLD"
            reason = f"Confidence too low: {confidence}% (min 65% required)"
        
        return {
            "trade_action": trade_action,
            "confidence": confidence,
            "reason": reason,
            "ml_consensus": signal.get('models_consensus', 'Unknown'),
            "signal_timestamp": signal['timestamp']
        }
    
    def generate_trade_parameters(self, symbol="EURUSD") -> Dict[str, any]:
        """Generiert Trading-Parameter basierend auf ML-Signal"""
        decision = self.should_execute_trade(symbol)
        
        if decision['trade_action'] == 'HOLD':
            return decision
        
        # Standard Trading-Parameter
        base_lot_size = 0.01  # Mini-Lot für Sicherheit
        
        # Lot-Größe basierend auf Confidence anpassen
        confidence = decision['confidence']
        if confidence >= 80:
            lot_multiplier = 2.0
        elif confidence >= 70:
            lot_multiplier = 1.5
        else:
            lot_multiplier = 1.0
        
        lot_size = base_lot_size * lot_multiplier
        
        # Stop Loss und Take Profit (konservativ)
        if decision['trade_action'] == 'BUY':
            sl_pips = 25  # 25 Pips Stop Loss
            tp_pips = 30  # 30 Pips Take Profit
        else:  # SELL
            sl_pips = 25
            tp_pips = 30
        
        decision.update({
            "symbol": symbol,
            "lot_size": lot_size,
            "sl_pips": sl_pips,
            "tp_pips": tp_pips,
            "trade_type": "MARKET",
            "valid_until": datetime.now() + timedelta(minutes=15)  # Signal 15 Min gültig
        })
        
        return decision

def test_ml_integration():
    """Test der ML-Trading-Integration"""
    print("ML Trading Integration Test")
    print("=" * 40)
    
    integration = MLTradingIntegration()
    
    # Signal laden
    signal = integration.get_ml_signal()
    if signal:
        print(f"✅ Current ML Signal loaded")
        print(f"   Action: {signal['action']}")
        print(f"   Confidence: {signal['confidence']}%")
        print(f"   Timestamp: {signal['timestamp']}")
    else:
        print("❌ No ML signal available")
        return
    
    # Trading-Entscheidung
    decision = integration.should_execute_trade()
    print(f"\n📊 Trading Decision:")
    print(f"   Action: {decision['trade_action']}")
    print(f"   Confidence: {decision['confidence']}%") 
    print(f"   Reason: {decision['reason']}")
    
    # Trading-Parameter
    if decision['trade_action'] != 'HOLD':
        params = integration.generate_trade_parameters()
        print(f"\n⚙️ Trading Parameters:")
        print(f"   Symbol: {params['symbol']}")
        print(f"   Lot Size: {params['lot_size']}")
        print(f"   Stop Loss: {params['sl_pips']} pips")
        print(f"   Take Profit: {params['tp_pips']} pips")
        print(f"   Valid Until: {params['valid_until']}")
        
        print(f"\n🎯 READY TO TRADE!")
        print(f"   - ML models provide {decision['trade_action']} signal")
        print(f"   - Confidence level acceptable ({decision['confidence']}%)")
        print(f"   - Trade parameters calculated")
        
    else:
        print(f"\n⏸️ NO TRADE - {decision['reason']}")

if __name__ == "__main__":
    test_ml_integration()

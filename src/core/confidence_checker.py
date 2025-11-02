#!/usr/bin/env python3
"""
Confidence Value Checker - Überprüft die Confidence-Werte in der Datenbank
"""

import sqlite3
from datetime import datetime

def check_confidence_values():
    """Überprüft die aktuellen Confidence-Werte"""
    
    print("🔍 CONFIDENCE VALUE CHECKER")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect("trading_robot.db")
        cursor = conn.cursor()
        
        # Get recent signals with confidence values
        cursor.execute("""
            SELECT id, timestamp, symbol, signal, confidence, entry_price
            FROM trading_signals 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        signals = cursor.fetchall()
        
        print(f"\n📊 Letzte 10 Signale:\n")
        print(f"{'ID':<5} {'Symbol':<8} {'Action':<6} {'Confidence':<12} {'Percentage':<12} {'Price':<10} {'Time'}")
        print("-" * 80)
        
        for signal in signals:
            signal_id, timestamp, symbol, action, confidence, price = signal
            
            # Convert confidence to percentage if it's decimal
            if confidence <= 1.0:
                confidence_percent = confidence * 100
                format_type = "Decimal"
            else:
                confidence_percent = confidence
                format_type = "Percent"
                
            print(f"{signal_id:<5} {symbol:<8} {action:<6} {confidence:<12.6f} {confidence_percent:<8.2f}% ({format_type:<7}) {price:<10.3f} {timestamp}")
        
        print("\n" + "=" * 50)
        print("🎯 ANALYSE:")
        
        # Check for problematic values
        problematic = [s for s in signals if s[4] < 1.0 and s[4] > 0.01]  # Decimal format but should be percentage
        
        if problematic:
            print(f"❌ Problem gefunden: {len(problematic)} Signale haben Decimal-Format statt Prozent!")
            print("   Das führt dazu, dass 79.78% als 0.7978% interpretiert wird!")
            print("\n💡 Lösung: Confidence-Werte müssen entweder:")
            print("   - Alle als Prozent (70.0 für 70%) ODER")
            print("   - Alle als Decimal (0.70 für 70%) gespeichert werden")
            print("   - UND das System muss entsprechend angepasst werden")
        else:
            print("✅ Confidence-Werte scheinen konsistent zu sein")
            
        # Check minimum confidence threshold
        print(f"\n🎯 Confidence-Schwellwert-Analyse:")
        high_conf = [s for s in signals if (s[4] * 100 if s[4] <= 1 else s[4]) >= 70]
        print(f"   Signale >= 70%: {len(high_conf)}")
        print(f"   Signale < 70%:  {len(signals) - len(high_conf)}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    check_confidence_values()

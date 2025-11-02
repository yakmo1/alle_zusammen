#!/usr/bin/env python3
"""
Trading Signal Activator für EURUSD
Stellt sicher, dass ML-Modelle Trades auslösen
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def check_ml_models():
    """Überprüft verfügbare ML-Modelle"""
    models_dir = os.path.join(current_dir, "..", "models")
    
    required_files = [
        "random_forest.joblib",
        "gradient_boost.joblib", 
        "neural_network.joblib",
        "svm.joblib",
        "scaler.joblib"
    ]
    
    print("Checking ML Models...")
    all_available = True
    
    for model_file in required_files:
        model_path = os.path.join(models_dir, model_file)
        if os.path.exists(model_path):
            size_kb = os.path.getsize(model_path) / 1024
            print(f"  Available: {model_file}: {size_kb:.1f} KB")
        else:
            print(f"  ❌ {model_file}: Missing")
            all_available = False
    
    return all_available

def generate_trading_signal():
    """Generiert aktuelles Trading-Signal"""
    try:
        from live_ml_predictor import LiveMLPredictor
        
        print("🤖 Generating Trading Signal...")
        predictor = LiveMLPredictor()
        predictions = predictor.get_predictions()
        
        if predictions:
            consensus = predictions['consensus']
            confidence = predictions['avg_confidence']
            
            print(f"📊 Current Signal: {consensus}")
            print(f"💪 Confidence: {confidence}%")
            print(f"🕐 Generated: {predictions['timestamp']}")
            
            # Determine trade action
            if consensus == 'BULLISH' and confidence > 65:
                action = "BUY Signal Active"
                emoji = "📈"
            elif consensus == 'BEARISH' and confidence > 65:
                action = "SELL Signal Active" 
                emoji = "📉"
            else:
                action = "HOLD - Low Confidence"
                emoji = "⏸️"
            
            print(f"\n🎯 TRADING ACTION: {emoji} {action}")
            
            # Save signal for trading system
            signal_data = {
                "action": consensus.lower(),
                "confidence": confidence,
                "timestamp": predictions['timestamp'],
                "models_consensus": predictions['consensus_strength'],
                "trade_recommendation": action
            }
            
            signal_file = os.path.join(current_dir, "..", "current_trading_signal.json")
            with open(signal_file, 'w') as f:
                json.dump(signal_data, f, indent=2)
            
            print(f"💾 Signal saved to: current_trading_signal.json")
            return True
            
        else:
            print("❌ Could not generate predictions")
            return False
            
    except Exception as e:
        print(f"❌ Error generating signal: {e}")
        return False

def check_eurusd_data():
    """Überprüft EURUSD Datenquelle"""
    try:
        import psycopg2
        
        print("📊 Checking EURUSD Data...")
        
        conn = psycopg2.connect(
            host='212.132.105.198', 
            database='trading_bot', 
            user='mt5user', 
            password='1234', 
            port=5432
        )
        cursor = conn.cursor()
        
        # Check today's table
        today = datetime.now().strftime('%Y%m%d')
        today_table = f"ticks_eurusd_{today}"
        
        try:
            cursor.execute(f"SELECT COUNT(*), MAX(time) FROM {today_table}")
            result = cursor.fetchone()
            print(f"  ✅ {today_table}: {result[0]} ticks, latest: {result[1]}")
            data_available = True
        except:
            print(f"  ⚠️ {today_table}: Not available")
            
            # Check fallback ticks table
            try:
                cursor.execute("SELECT COUNT(*) FROM ticks WHERE symbol = 'EURUSD'")
                result = cursor.fetchone()
                print(f"  ✅ Fallback ticks: {result[0]} EURUSD records")
                data_available = True
            except:
                print(f"  ❌ No EURUSD data available")
                data_available = False
        
        conn.close()
        return data_available
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    print("EURUSD Trading Signal Activator")
    print("=" * 40)
    
    # Check all components
    models_ok = check_ml_models()
    data_ok = check_eurusd_data() 
    signal_ok = generate_trading_signal()
    
    print("\n" + "=" * 40)
    print("SYSTEM STATUS SUMMARY:")
    print("=" * 40)
    
    print(f"ML Models: {'✅ Available' if models_ok else '❌ Missing'}")
    print(f"EURUSD Data: {'✅ Available' if data_ok else '❌ Missing'}")
    print(f"Trading Signal: {'✅ Generated' if signal_ok else '❌ Failed'}")
    
    if models_ok and data_ok and signal_ok:
        print(f"\n🎉 TRADING SYSTEM READY!")
        print(f"   - ML models loaded and functional")
        print(f"   - Live EURUSD data available") 
        print(f"   - Trading signals being generated")
        print(f"   - Dashboard should show live predictions")
        
        # Instructions
        print(f"\n📋 TO ACTIVATE TRADING:")
        print(f"   1. Check Dashboard: http://localhost:5000/prediction-details")
        print(f"   2. Verify ML predictions are visible")
        print(f"   3. Monitor current_trading_signal.json for signals")
        print(f"   4. Enable trading in system config if needed")
        
    else:
        print(f"\n⚠️ SYSTEM ISSUES DETECTED")
        if not models_ok:
            print(f"   - Run: python core/intelligent_ml_trainer.py")
        if not data_ok:
            print(f"   - Run: python core/daily_table_manager.py")
        if not signal_ok:
            print(f"   - Check ML model loading errors")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Live ML Prediction Integration for Dashboard
Verbindet die trainierten ML Modelle mit dem Dashboard
"""

import os
import joblib
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime
import json

class LiveMLPredictor:
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        self.models = {}
        self.scaler = None
        self.load_models()
    
    def load_models(self):
        """Lädt trainierte ML Modelle"""
        if not os.path.exists(self.models_dir):
            print(f"Models directory {self.models_dir} not found")
            return
        
        try:
            # Load scaler
            scaler_path = os.path.join(self.models_dir, "scaler.joblib")
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                print("✅ Scaler loaded")
            
            # Load models
            model_files = ['random_forest.joblib', 'gradient_boost.joblib', 
                          'neural_network.joblib', 'svm.joblib']
            
            for model_file in model_files:
                model_path = os.path.join(self.models_dir, model_file)
                if os.path.exists(model_path):
                    model_name = model_file.replace('.joblib', '')
                    self.models[model_name] = joblib.load(model_path)
                    print(f"✅ {model_name} model loaded")
            
        except Exception as e:
            print(f"❌ Error loading models: {e}")
    
    def get_current_eurusd_data(self):
        """Holt aktuelle EURUSD Daten für Prediction"""
        try:
            conn = psycopg2.connect(
                host='212.132.105.198', 
                database='trading_bot', 
                user='mt5user', 
                password='1234', 
                port=5432
            )
            cursor = conn.cursor()
            
            # Try today's table first
            today = datetime.now().strftime('%Y%m%d')
            today_table = f"ticks_eurusd_{today}"
            
            try:
                cursor.execute(f"""
                    SELECT bid, ask, time 
                    FROM {today_table} 
                    WHERE bid IS NOT NULL AND ask IS NOT NULL 
                    ORDER BY time DESC 
                    LIMIT 50
                """)
                data = cursor.fetchall()
                source = today_table
            except:
                # Fallback to ticks table
                cursor.execute("""
                    SELECT bid, ask, time 
                    FROM ticks 
                    WHERE symbol = 'EURUSD' AND bid IS NOT NULL AND ask IS NOT NULL 
                    ORDER BY time DESC 
                    LIMIT 50
                """)
                data = cursor.fetchall()
                source = 'ticks'
            
            conn.close()
            return data, source
            
        except Exception as e:
            print(f"Error getting current data: {e}")
            return None, None
    
    def prepare_features(self, data):
        """Bereitet Features wie im Training vor"""
        if not data or len(data) < 20:
            return None
        
        # Convert to DataFrame (reverse for chronological order)
        df = pd.DataFrame(data[::-1], columns=['bid', 'ask', 'time'])
        df['bid'] = pd.to_numeric(df['bid'])
        df['ask'] = pd.to_numeric(df['ask'])
        df['mid'] = (df['bid'] + df['ask']) / 2
        df['spread'] = df['ask'] - df['bid']
        
        # Create same features as in training
        df['price_change'] = df['mid'].diff()
        df['price_change_5'] = df['mid'].diff(5)
        df['price_change_10'] = df['mid'].diff(10)
        
        # Moving averages
        df['ma_5'] = df['mid'].rolling(5).mean()
        df['ma_10'] = df['mid'].rolling(10).mean()
        df['ma_20'] = df['mid'].rolling(20).mean()
        
        # Volatility features
        df['volatility_5'] = df['mid'].rolling(5).std()
        df['volatility_10'] = df['mid'].rolling(10).std()
        
        # Trend indicators
        df['trend_5'] = (df['mid'] > df['ma_5']).astype(int)
        df['trend_10'] = (df['mid'] > df['ma_10']).astype(int)
        
        # Remove NaN values
        df = df.dropna()
        
        if len(df) == 0:
            return None
        
        # Feature columns (same as training)
        feature_columns = ['bid', 'ask', 'spread', 'price_change', 'price_change_5', 
                          'price_change_10', 'ma_5', 'ma_10', 'ma_20', 
                          'volatility_5', 'volatility_10', 'trend_5', 'trend_10']
        
        return df[feature_columns].values[-1:]  # Return latest features only
    
    def get_predictions(self):
        """Macht Live Predictions mit allen Modellen"""
        if not self.models:
            return None
        
        # Get current data
        data, source = self.get_current_eurusd_data()
        if not data:
            return None
        
        # Prepare features
        features = self.prepare_features(data)
        if features is None:
            return None
        
        predictions = {}
        confidences = {}
        
        for name, model in self.models.items():
            try:
                # Apply scaling for neural network and SVM
                if name in ['neural_network', 'svm'] and self.scaler:
                    features_scaled = self.scaler.transform(features)
                    pred = model.predict(features_scaled)[0]
                    prob = model.predict_proba(features_scaled)[0]
                else:
                    pred = model.predict(features)[0]
                    prob = model.predict_proba(features)[0]
                
                predictions[name] = 'BULLISH' if pred == 1 else 'BEARISH'
                confidences[name] = round(max(prob) * 100, 1)
                
            except Exception as e:
                print(f"Error predicting with {name}: {e}")
                predictions[name] = 'NEUTRAL'
                confidences[name] = 50.0
        
        # Calculate consensus
        bullish_count = sum(1 for p in predictions.values() if p == 'BULLISH')
        total_models = len(predictions)
        
        if bullish_count > total_models // 2:
            consensus = 'BULLISH'
        elif bullish_count < total_models // 2:
            consensus = 'BEARISH'
        else:
            consensus = 'NEUTRAL'
        
        # Calculate average confidence
        avg_confidence = round(sum(confidences.values()) / len(confidences), 1)
        
        return {
            'predictions': predictions,
            'confidences': confidences,
            'consensus': consensus,
            'consensus_strength': f"{max(bullish_count, total_models - bullish_count)}/{total_models}",
            'avg_confidence': avg_confidence,
            'data_source': source,
            'total_models': total_models,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# Test the system
if __name__ == "__main__":
    print("Live ML Prediction System Test")
    print("=" * 40)
    
    predictor = LiveMLPredictor()
    
    if predictor.models:
        result = predictor.get_predictions()
        
        if result:
            print("🤖 LIVE ML PREDICTIONS:")
            print(f"   Data Source: {result['data_source']}")
            print(f"   Timestamp: {result['timestamp']}")
            print("\n📊 Individual Models:")
            
            for name, prediction in result['predictions'].items():
                confidence = result['confidences'][name]
                emoji = "📈" if prediction == 'BULLISH' else "📉" if prediction == 'BEARISH' else "➡️"
                print(f"   {emoji} {name.replace('_', ' ').title()}: {prediction} ({confidence}%)")
            
            print(f"\n🎯 CONSENSUS: {result['consensus']} ({result['consensus_strength']} models)")
            print(f"💪 Average Confidence: {result['avg_confidence']}%")
            
            # Save prediction for dashboard
            with open('latest_prediction.json', 'w') as f:
                json.dump(result, f, indent=2)
            
            print("✅ Prediction saved for dashboard integration")
        else:
            print("❌ Could not generate predictions")
    else:
        print("❌ No trained models available. Run intelligent_ml_trainer.py first.")

#!/usr/bin/env python3
"""
Intelligentes EURUSD ML Training System
Nutzt tagesbasierte Tabellen für optimales Machine Learning Training
"""

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

class EURUSDMLTrainer:
    def __init__(self):
        self.models = {
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'gradient_boost': GradientBoostingClassifier(n_estimators=100, random_state=42),
            'neural_network': MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=1000, random_state=42),
            'svm': SVC(kernel='rbf', probability=True, random_state=42)
        }
        self.scaler = StandardScaler()
        self.trained_models = {}
        
    def get_training_data(self, days_back=7):
        """
        Sammelt EURUSD Trainingsdaten aus mehreren Tagen
        """
        try:
            conn = psycopg2.connect(
                host='212.132.105.198', 
                database='trading_bot', 
                user='mt5user', 
                password='1234', 
                port=5432
            )
            cursor = conn.cursor()
            
            all_data = []
            tables_used = []
            
            # Sammle Daten aus den letzten Tagen
            for i in range(days_back):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
                table_name = f"ticks_eurusd_{date}"
                
                try:
                    cursor.execute(f"""
                        SELECT bid, ask, time 
                        FROM {table_name} 
                        WHERE bid IS NOT NULL AND ask IS NOT NULL
                        ORDER BY time ASC
                    """)
                    table_data = cursor.fetchall()
                    if table_data:
                        all_data.extend(table_data)
                        tables_used.append(f"{table_name} ({len(table_data)} ticks)")
                except:
                    print(f"Table {table_name} not available")
            
            # Fallback: Nutze allgemeine ticks Tabelle
            if not all_data:
                try:
                    cursor.execute("""
                        SELECT bid, ask, time 
                        FROM ticks 
                        WHERE symbol = 'EURUSD' AND bid IS NOT NULL AND ask IS NOT NULL
                        ORDER BY time ASC
                    """)
                    table_data = cursor.fetchall()
                    if table_data:
                        all_data.extend(table_data)
                        tables_used.append(f"ticks ({len(table_data)} EURUSD ticks)")
                except Exception as e:
                    print(f"Error accessing ticks table: {e}")
            
            conn.close()
            
            print(f"Training data collected from {len(tables_used)} sources:")
            for source in tables_used:
                print(f"  - {source}")
            
            return all_data
            
        except Exception as e:
            print(f"Error collecting training data: {e}")
            return []
    
    def prepare_features(self, data):
        """
        Bereitet Features für ML Training vor
        """
        if len(data) < 20:
            print("Not enough data for feature preparation")
            return None, None
        
        # Convert to DataFrame
        df = pd.DataFrame(data, columns=['bid', 'ask', 'time'])
        df['bid'] = pd.to_numeric(df['bid'])
        df['ask'] = pd.to_numeric(df['ask'])
        df['mid'] = (df['bid'] + df['ask']) / 2
        df['spread'] = df['ask'] - df['bid']
        
        # Create features
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
        
        # Create target (next price direction)
        df['target'] = (df['mid'].shift(-1) > df['mid']).astype(int)
        
        # Remove NaN values
        df = df.dropna()
        
        if len(df) < 10:
            print("Not enough data after feature engineering")
            return None, None
        
        # Feature columns
        feature_columns = ['bid', 'ask', 'spread', 'price_change', 'price_change_5', 
                          'price_change_10', 'ma_5', 'ma_10', 'ma_20', 
                          'volatility_5', 'volatility_10', 'trend_5', 'trend_10']
        
        X = df[feature_columns].values
        y = df['target'].values[:-1]  # Remove last target (no future data)
        X = X[:-1]  # Align X with y
        
        return X, y
    
    def train_models(self, X, y):
        """
        Trainiert alle ML Modelle
        """
        if X is None or y is None or len(X) < 10:
            print("Insufficient data for training")
            return
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        print(f"\nTraining models on {len(X_train)} samples...")
        print("=" * 50)
        
        results = {}
        
        for name, model in self.models.items():
            try:
                print(f"\nTraining {name}...")
                
                # Train model
                if name == 'neural_network':
                    model.fit(X_train_scaled, y_train)
                    y_pred = model.predict(X_test_scaled)
                elif name == 'svm':
                    model.fit(X_train_scaled, y_train)
                    y_pred = model.predict(X_test_scaled)
                else:
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)
                
                # Calculate accuracy
                accuracy = accuracy_score(y_test, y_pred)
                results[name] = accuracy
                
                # Store trained model
                self.trained_models[name] = model
                
                print(f"✅ {name}: {accuracy:.2%} accuracy")
                
                # Detailed report for best models
                if accuracy > 0.55:  # Above random chance
                    print(f"   Classification Report:")
                    report = classification_report(y_test, y_pred, target_names=['DOWN', 'UP'])
                    print(f"   {report.replace(newline, newline + '   ')}")
                
            except Exception as e:
                print(f"❌ Error training {name}: {e}")
                results[name] = 0.0
        
        return results
    
    def save_models(self):
        """
        Speichert trainierte Modelle
        """
        models_dir = "models"
        os.makedirs(models_dir, exist_ok=True)
        
        try:
            # Save scaler
            joblib.dump(self.scaler, f"{models_dir}/scaler.joblib")
            
            # Save models
            for name, model in self.trained_models.items():
                joblib.dump(model, f"{models_dir}/{name}.joblib")
            
            print(f"\n✅ Models saved to {models_dir}/ directory")
            
        except Exception as e:
            print(f"❌ Error saving models: {e}")
    
    def get_live_prediction(self):
        """
        Macht eine Live Prediction mit aktuellen Daten
        """
        try:
            # Get current data
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
            
            cursor.execute(f"""
                SELECT bid, ask, time 
                FROM {today_table} 
                WHERE bid IS NOT NULL AND ask IS NOT NULL 
                ORDER BY time DESC 
                LIMIT 50
            """)
            current_data = cursor.fetchall()
            conn.close()
            
            if len(current_data) < 20:
                print("Not enough current data for prediction")
                return None
            
            # Prepare features for current data
            X_current, _ = self.prepare_features(current_data[::-1])  # Reverse for chronological order
            
            if X_current is None or len(X_current) == 0:
                print("Could not prepare features for current data")
                return None
            
            # Get latest features
            latest_features = X_current[-1:] 
            
            predictions = {}
            confidences = {}
            
            for name, model in self.trained_models.items():
                try:
                    if name in ['neural_network', 'svm']:
                        latest_scaled = self.scaler.transform(latest_features)
                        pred = model.predict(latest_scaled)[0]
                        prob = model.predict_proba(latest_scaled)[0]
                    else:
                        pred = model.predict(latest_features)[0]
                        prob = model.predict_proba(latest_features)[0]
                    
                    predictions[name] = 'UP' if pred == 1 else 'DOWN'
                    confidences[name] = max(prob)
                    
                except Exception as e:
                    print(f"Error predicting with {name}: {e}")
            
            return predictions, confidences
            
        except Exception as e:
            print(f"Error making live prediction: {e}")
            return None

def main():
    print("EURUSD Intelligent ML Training System")
    print("=" * 50)
    
    trainer = EURUSDMLTrainer()
    
    # Collect training data
    print("1. Collecting training data...")
    data = trainer.get_training_data(days_back=7)
    
    if not data:
        print("❌ No training data available")
        return
    
    print(f"✅ Collected {len(data)} total ticks for training")
    
    # Prepare features
    print("\n2. Preparing features...")
    X, y = trainer.prepare_features(data)
    
    if X is None:
        print("❌ Could not prepare features")
        return
    
    print(f"✅ Prepared {len(X)} training samples with {X.shape[1]} features")
    
    # Train models
    print("\n3. Training ML models...")
    results = trainer.train_models(X, y)
    
    # Show results
    print("\n" + "=" * 50)
    print("TRAINING RESULTS:")
    print("=" * 50)
    
    best_model = None
    best_accuracy = 0
    
    for name, accuracy in results.items():
        status = "✅" if accuracy > 0.55 else "⚠️" if accuracy > 0.50 else "❌"
        print(f"{status} {name.replace('_', ' ').title()}: {accuracy:.2%}")
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model = name
    
    print(f"\n🏆 Best Model: {best_model.replace('_', ' ').title()} ({best_accuracy:.2%})")
    
    # Save models
    print("\n4. Saving models...")
    trainer.save_models()
    
    # Make live prediction
    print("\n5. Making live prediction...")
    prediction_result = trainer.get_live_prediction()
    
    if prediction_result:
        predictions, confidences = prediction_result
        print("🔮 LIVE PREDICTIONS:")
        for name, pred in predictions.items():
            conf = confidences.get(name, 0)
            print(f"   {name.replace('_', ' ').title()}: {pred} ({conf:.1%} confidence)")
        
        # Consensus
        up_votes = sum(1 for p in predictions.values() if p == 'UP')
        down_votes = len(predictions) - up_votes
        
        consensus = "BULLISH 📈" if up_votes > down_votes else "BEARISH 📉"
        print(f"\n🎯 CONSENSUS: {consensus} ({up_votes}/{len(predictions)} models agree)")
    
    print(f"\n✅ Training complete! Use the models for live trading.")

if __name__ == "__main__":
    main()

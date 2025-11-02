#!/usr/bin/env python3
"""
ML Performance Optimizer - Kontinuierliche Verbesserung von 60% auf 95% Win Rate
Implementiert Machine Learning für Trading-Optimierung gemäß automation.instructions.md
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import warnings
warnings.filterwarnings('ignore')

# Lokale Imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.postgresql_manager import PostgreSQLManager
from dotenv import load_dotenv

load_dotenv()

class MLPerformanceOptimizer:
    """
    Machine Learning System für kontinuierliche Trading-Performance-Optimierung
    Ziel: Verbesserung von 60-70% auf bis zu 95% Win Rate
    """
    
    def __init__(self):
        self.db = PostgreSQLManager()
        
        self.models_dir = "ml_models"
        os.makedirs(self.models_dir, exist_ok=True)
        
        self.feature_columns = [
            'rsi', 'macd', 'ema_fast', 'ema_slow', 'bollinger_upper', 'bollinger_lower',
            'volume_ratio', 'price_momentum', 'volatility', 'market_session',
            'time_of_day', 'day_of_week', 'spread', 'market_sentiment'
        ]
        
        self.current_model = None
        self.scaler = StandardScaler()
        
    def prepare_training_data(self, days: int = 90, min_samples: int = 100) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Bereitet Trainingsdaten vor
        
        Args:
            days: Anzahl Tage für Trainingsdaten
            min_samples: Mindestanzahl Samples
            
        Returns:
            Tuple (Features DataFrame, Target Series)
        """
        
        print(f"📊 Bereite Trainingsdaten vor ({days} Tage)...")
        
        # Erweiterte Datenabfrage mit technischen Indikatoren
        query = """
            SELECT 
                t.symbol,
                t.profit_loss,
                t.open_time,
                t.close_time,
                t.confidence_score,
                t.market_conditions,
                md.technical_indicators,
                EXTRACT(hour FROM t.open_time) as hour_of_day,
                EXTRACT(dow FROM t.open_time) as day_of_week,
                CASE WHEN t.profit_loss > 0 THEN 1 ELSE 0 END as is_profitable
            FROM trades t
            LEFT JOIN market_data_cache md ON (
                t.symbol = md.symbol 
                AND DATE_TRUNC('minute', t.open_time) = DATE_TRUNC('minute', md.timestamp)
            )
            WHERE t.close_time IS NOT NULL 
            AND t.close_time >= CURRENT_DATE - INTERVAL '%s days'
            AND t.market_conditions IS NOT NULL
            ORDER BY t.close_time DESC
        """
        
        results = self.db.fetch_all(query, (days,))
        
        if len(results) < min_samples:
            raise ValueError(f"Nicht genügend Trainingsdaten: {len(results)} < {min_samples}")
        
        # DataFrame erstellen
        df = pd.DataFrame(results, columns=[
            'symbol', 'profit_loss', 'open_time', 'close_time', 'confidence_score',
            'market_conditions', 'technical_indicators', 'hour_of_day', 'day_of_week', 'is_profitable'
        ])
        
        # Features extrahieren
        features_df = self._extract_features(df)
        
        # Target Variable
        target = df['is_profitable']
        
        print(f"✅ Trainingsdaten vorbereitet: {len(features_df)} Samples mit {len(features_df.columns)} Features")
        
        return features_df, target
    
    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extrahiert und engineert Features für ML-Training"""
        
        features_list = []
        
        for _, row in df.iterrows():
            feature_dict = {}
            
            # Basis-Features
            feature_dict['confidence_score'] = row['confidence_score'] or 0.5
            feature_dict['hour_of_day'] = row['hour_of_day']
            feature_dict['day_of_week'] = row['day_of_week']
            
            # Market Conditions Features
            if row['market_conditions']:
                market_cond = json.loads(row['market_conditions']) if isinstance(row['market_conditions'], str) else row['market_conditions']
                feature_dict['spread'] = market_cond.get('spread', 0)
                feature_dict['volatility'] = market_cond.get('volatility', 0)
                feature_dict['market_session'] = self._encode_market_session(market_cond.get('session', 'unknown'))
                feature_dict['market_sentiment'] = market_cond.get('sentiment', 0)
            else:
                feature_dict.update({'spread': 0, 'volatility': 0, 'market_session': 0, 'market_sentiment': 0})
            
            # Technical Indicators Features
            if row['technical_indicators']:
                tech_ind = json.loads(row['technical_indicators']) if isinstance(row['technical_indicators'], str) else row['technical_indicators']
                feature_dict['rsi'] = tech_ind.get('rsi', 50)
                feature_dict['macd'] = tech_ind.get('macd', 0)
                feature_dict['ema_fast'] = tech_ind.get('ema_fast', 0)
                feature_dict['ema_slow'] = tech_ind.get('ema_slow', 0)
                feature_dict['bollinger_upper'] = tech_ind.get('bollinger_upper', 0)
                feature_dict['bollinger_lower'] = tech_ind.get('bollinger_lower', 0)
                feature_dict['volume_ratio'] = tech_ind.get('volume_ratio', 1)
                feature_dict['price_momentum'] = tech_ind.get('price_momentum', 0)
            else:
                feature_dict.update({
                    'rsi': 50, 'macd': 0, 'ema_fast': 0, 'ema_slow': 0,
                    'bollinger_upper': 0, 'bollinger_lower': 0, 'volume_ratio': 1, 'price_momentum': 0
                })
            
            # Symbol encoding
            feature_dict['symbol_encoded'] = self._encode_symbol(row['symbol'])
            
            features_list.append(feature_dict)
        
        return pd.DataFrame(features_list)
    
    def _encode_market_session(self, session: str) -> int:
        """Kodiert Market Session als numerischen Wert"""
        session_map = {'asian': 1, 'european': 2, 'american': 3, 'overlap': 4, 'unknown': 0}
        return session_map.get(session.lower(), 0)
    
    def _encode_symbol(self, symbol: str) -> int:
        """Kodiert Trading Symbol als numerischen Wert"""
        symbol_map = {'EURUSD': 1, 'GBPUSD': 2, 'USDJPY': 3, 'USDCAD': 4, 'AUDUSD': 5, 'USDCHF': 6}
        return symbol_map.get(symbol, 0)
    
    def train_optimization_model(self, retrain: bool = False) -> Dict[str, Any]:
        """
        Trainiert ML-Model für Trading-Optimierung
        
        Args:
            retrain: Ob Model neu trainiert werden soll
            
        Returns:
            Dict mit Training-Ergebnissen
        """
        
        print("🤖 Starte ML-Model Training...")
        
        try:
            # Trainingsdaten laden
            X, y = self.prepare_training_data()
            
            # Train-Test Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Feature Scaling
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Model Selection und Hyperparameter Tuning
            models = {
                'RandomForest': {
                    'model': RandomForestClassifier(random_state=42),
                    'params': {
                        'n_estimators': [100, 200, 300],
                        'max_depth': [10, 20, None],
                        'min_samples_split': [2, 5, 10],
                        'min_samples_leaf': [1, 2, 4]
                    }
                },
                'GradientBoosting': {
                    'model': GradientBoostingClassifier(random_state=42),
                    'params': {
                        'n_estimators': [100, 200],
                        'learning_rate': [0.05, 0.1, 0.15],
                        'max_depth': [3, 5, 7],
                        'min_samples_split': [2, 5, 10]
                    }
                }
            }
            
            best_model = None
            best_score = 0
            best_model_name = ""
            model_results = {}
            
            # Grid Search für jedes Model
            for model_name, model_config in models.items():
                print(f"  🔄 Trainiere {model_name}...")
                
                grid_search = GridSearchCV(
                    model_config['model'],
                    model_config['params'],
                    cv=5,
                    scoring='accuracy',
                    n_jobs=-1,
                    verbose=0
                )
                
                grid_search.fit(X_train_scaled, y_train)
                
                # Evaluation
                y_pred = grid_search.best_estimator_.predict(X_test_scaled)
                
                accuracy = accuracy_score(y_test, y_pred)
                precision = precision_score(y_test, y_pred, average='weighted')
                recall = recall_score(y_test, y_pred, average='weighted')
                f1 = f1_score(y_test, y_pred, average='weighted')
                
                model_results[model_name] = {
                    'accuracy': round(accuracy, 4),
                    'precision': round(precision, 4),
                    'recall': round(recall, 4),
                    'f1_score': round(f1, 4),
                    'best_params': grid_search.best_params_
                }
                
                print(f"    Accuracy: {accuracy:.3f}")
                
                if accuracy > best_score:
                    best_score = accuracy
                    best_model = grid_search.best_estimator_
                    best_model_name = model_name
            
            # Bestes Model speichern
            self.current_model = best_model
            
            # Model und Scaler speichern
            model_filename = f"best_trading_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
            scaler_filename = f"feature_scaler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
            
            model_path = os.path.join(self.models_dir, model_filename)
            scaler_path = os.path.join(self.models_dir, scaler_filename)
            
            joblib.dump(best_model, model_path)
            joblib.dump(self.scaler, scaler_path)
            
            # Feature Importance
            if hasattr(best_model, 'feature_importances_'):
                feature_importance = dict(zip(X.columns, best_model.feature_importances_))
                feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
            else:
                feature_importance = {}
            
            # Ergebnisse in DB speichern
            self._save_model_performance(best_model_name, model_results[best_model_name], feature_importance, model_path)
            
            training_results = {
                'best_model': best_model_name,
                'best_accuracy': round(best_score, 4),
                'model_results': model_results,
                'feature_importance': feature_importance,
                'model_path': model_path,
                'scaler_path': scaler_path,
                'training_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
            print(f"✅ Training abgeschlossen! Bestes Model: {best_model_name} (Accuracy: {best_score:.3f})")
            
            return training_results
            
        except Exception as e:
            print(f"❌ Fehler beim Model Training: {e}")
            return {}
    
    def predict_trade_success(self, market_data: Dict, confidence_score: float = 0.5) -> Dict[str, Any]:
        """
        Vorhersage für Trade-Erfolg
        
        Args:
            market_data: Market Data Dictionary
            confidence_score: Basis-Confidence Score
            
        Returns:
            Dict mit Vorhersage und Confidence
        """
        
        if self.current_model is None:
            return {'prediction': 1, 'confidence': confidence_score, 'ml_enabled': False}
        
        try:
            # Features aus Market Data extrahieren
            features = self._extract_features_from_market_data(market_data, confidence_score)
            
            # Vorhersage
            features_scaled = self.scaler.transform([features])
            prediction = self.current_model.predict(features_scaled)[0]
            prediction_proba = self.current_model.predict_proba(features_scaled)[0]
            
            ml_confidence = max(prediction_proba)
            
            return {
                'prediction': int(prediction),
                'confidence': round(ml_confidence, 3),
                'ml_enabled': True,
                'prediction_proba': prediction_proba.tolist()
            }
            
        except Exception as e:
            print(f"⚠️ Fehler bei ML-Vorhersage: {e}")
            return {'prediction': 1, 'confidence': confidence_score, 'ml_enabled': False}
    
    def _extract_features_from_market_data(self, market_data: Dict, confidence_score: float) -> List[float]:
        """Extrahiert Features aus aktuellen Market Data"""
        
        now = datetime.now()
        
        features = [
            market_data.get('rsi', 50),
            market_data.get('macd', 0),
            market_data.get('ema_fast', 0),
            market_data.get('ema_slow', 0),
            market_data.get('bollinger_upper', 0),
            market_data.get('bollinger_lower', 0),
            market_data.get('volume_ratio', 1),
            market_data.get('price_momentum', 0),
            market_data.get('volatility', 0),
            self._encode_market_session(market_data.get('session', 'unknown')),
            now.hour,
            now.weekday(),
            market_data.get('spread', 0),
            market_data.get('sentiment', 0),
            confidence_score,
            self._encode_symbol(market_data.get('symbol', 'EURUSD'))
        ]
        
        return features
    
    def _save_model_performance(self, model_name: str, performance: Dict, feature_importance: Dict, model_path: str):
        """Speichert Model Performance in Datenbank"""
        
        query = """
            INSERT INTO ml_model_performance 
            (model_name, model_version, accuracy, precision_score, recall_score, f1_score, 
             is_active, feature_importance, hyperparameters)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Alte Models deaktivieren
        self.db.execute_query("UPDATE ml_model_performance SET is_active = FALSE")
        
        # Neues Model speichern
        version = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        self.db.execute_query(query, (
            model_name,
            version,
            performance['accuracy'],
            performance['precision'],
            performance['recall'],
            performance['f1_score'],
            True,  # is_active = True (PostgreSQL verwendet TRUE/FALSE)
            json.dumps(feature_importance),
            json.dumps(performance['best_params'])
        ))
    
    def load_latest_model(self) -> bool:
        """Lädt das neueste aktive ML-Model"""
        
        try:
            # Neuestes aktives Model aus DB
            query = """
                SELECT model_name, model_version, accuracy
                FROM ml_model_performance 
                WHERE is_active = TRUE
                ORDER BY training_date DESC
                LIMIT 1
            """
            
            result = self.db.fetch_one(query)
            
            if not result:
                print("ℹ️ Kein aktives ML-Model gefunden")
                return False
            
            # Model-Dateien suchen
            model_files = [f for f in os.listdir(self.models_dir) if f.endswith('.joblib') and 'model' in f]
            scaler_files = [f for f in os.listdir(self.models_dir) if f.endswith('.joblib') and 'scaler' in f]
            
            if model_files and scaler_files:
                # Neueste Dateien laden
                latest_model_file = max(model_files, key=lambda x: os.path.getctime(os.path.join(self.models_dir, x)))
                latest_scaler_file = max(scaler_files, key=lambda x: os.path.getctime(os.path.join(self.models_dir, x)))
                
                model_path = os.path.join(self.models_dir, latest_model_file)
                scaler_path = os.path.join(self.models_dir, latest_scaler_file)
                
                self.current_model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                
                print(f"✅ ML-Model geladen: {result[0]} (Accuracy: {result[2]:.3f})")
                return True
            else:
                print("⚠️ Model-Dateien nicht gefunden")
                return False
                
        except Exception as e:
            print(f"❌ Fehler beim Laden des Models: {e}")
            return False
    
    def auto_retrain_if_needed(self, min_accuracy: float = 0.65, days_since_training: int = 7) -> bool:
        """
        Automatisches Retraining wenn Performance unter Schwellwert
        
        Args:
            min_accuracy: Mindest-Accuracy für Retraining
            days_since_training: Tage seit letztem Training
            
        Returns:
            True wenn retrained wurde
        """
        
        # Prüfe letzte Model Performance
        query = """
            SELECT accuracy, training_date
            FROM ml_model_performance 
            WHERE is_active = 1
            ORDER BY training_date DESC
            LIMIT 1
        """
        
        result = self.db.fetch_one(query)
        
        if not result:
            print("🔄 Kein aktives Model - starte Training...")
            self.train_optimization_model()
            return True
        
        accuracy, training_date = result
        days_old = (datetime.now() - training_date).days
        
        if accuracy < min_accuracy or days_old > days_since_training:
            print(f"🔄 Retraining erforderlich (Accuracy: {accuracy:.3f}, Alter: {days_old} Tage)")
            self.train_optimization_model(retrain=True)
            return True
        
        return False

def main():
    """Hauptfunktion für ML-Optimierung"""
    
    print("🤖 Starte ML Performance Optimizer...")
    
    try:
        optimizer = MLPerformanceOptimizer()
        
        # Model laden oder trainieren
        if not optimizer.load_latest_model():
            print("🔄 Starte initiales Model Training...")
            results = optimizer.train_optimization_model()
            
            if results:
                print(f"\n✅ Training erfolgreich:")
                print(f"  Bestes Model: {results['best_model']}")
                print(f"  Accuracy: {results['best_accuracy']}")
                print(f"  Training Samples: {results['training_samples']}")
        
        # Auto-Retraining prüfen
        optimizer.auto_retrain_if_needed()
        
        print("\n🚀 ML Optimizer bereit für Trading-Optimierung!")
        
    except Exception as e:
        print(f"❌ Fehler im ML Optimizer: {e}")

if __name__ == "__main__":
    main()

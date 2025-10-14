#!/usr/bin/env python3
"""
Market Regime Detector - Automatische Erkennung von Marktphasen
Erweiterte ML-basierte Klassifikation von Bullish/Bearish/Sideways Märkten
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import joblib
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

# Lokale Imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.postgresql_manager import PostgreSQLManager

class MarketRegimeDetector:
    """
    Erweiterte Market Regime Detection
    - Bullish/Bearish/Sideways Klassifikation
    - Volatilitäts-Regime Erkennung
    - Anomalie-Detection für Market Shocks
    - Real-time Regime Updates
    """
    
    def __init__(self):
        self.db = PostgreSQLManager()
        
        self.models_dir = "ml_models"
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Regime Models
        self.regime_classifier = None
        self.volatility_detector = None
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        
        # Current State
        self.current_regime = "NEUTRAL"
        self.current_volatility = "MEDIUM"
        self.regime_confidence = 0.0
        self.last_update = None
        
        # Regime Features
        self.regime_features = [
            'price_trend_5', 'price_trend_15', 'price_trend_60',
            'volatility_5', 'volatility_15', 'volatility_60',
            'volume_trend', 'momentum_strength', 'trend_consistency',
            'support_resistance_strength', 'breakout_probability'
        ]
        
        print("🔮 Market Regime Detector initialisiert")
    
    def analyze_market_data_for_regimes(self, symbol: str = "EURUSD", periods: int = 500) -> pd.DataFrame:
        """
        Analysiert Marktdaten zur Regime-Erkennung
        """
        print(f"📊 Analysiere Marktdaten für Regime-Erkennung: {symbol}")
        
        try:
            # Simuliere Marktdaten (in echter Implementierung würde MT5-Daten verwendet)
            data = self._generate_market_data(symbol, periods)
            
            # Feature Engineering für Regime-Erkennung
            data = self._engineer_regime_features(data)
            
            # Regime-Labels basierend auf technischen Indikatoren
            data = self._classify_historical_regimes(data)
            
            print(f"✅ {len(data)} Datenpunkte analysiert")
            return data
            
        except Exception as e:
            print(f"❌ Marktdaten-Analyse Fehler: {e}")
            return pd.DataFrame()
    
    def _generate_market_data(self, symbol: str, periods: int) -> pd.DataFrame:
        """Generiert realistische Marktdaten für Demo"""
        np.random.seed(42)
        
        # Basis-Parameter für verschiedene Symbole
        base_prices = {
            'EURUSD': 1.0850, 'GBPUSD': 1.2750, 'USDJPY': 145.50,
            'USDCAD': 1.3650, 'AUDUSD': 0.6750
        }
        
        base_price = base_prices.get(symbol, 1.0000)
        
        # Generiere realistische Preis-Serie
        dates = pd.date_range(start=datetime.now() - timedelta(days=periods), periods=periods, freq='H')
        
        # Random Walk mit Trend-Komponenten
        returns = np.random.normal(0, 0.001, periods)
        
        # Füge Trend-Phasen hinzu
        trend_length = periods // 10
        for i in range(0, periods, trend_length):
            end_idx = min(i + trend_length, periods)
            trend_direction = np.random.choice([-1, 0, 1])  # Bearish, Sideways, Bullish
            trend_strength = np.random.uniform(0.0001, 0.0005)
            returns[i:end_idx] += trend_direction * trend_strength
        
        # Preis-Serie berechnen
        prices = [base_price]
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        # Volume simulieren
        volumes = np.random.lognormal(10, 0.5, periods)
        
        # DataFrame erstellen
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices[:-1],
            'high': [p * (1 + np.random.uniform(0, 0.002)) for p in prices[:-1]],
            'low': [p * (1 - np.random.uniform(0, 0.002)) for p in prices[:-1]],
            'close': prices[1:],
            'volume': volumes
        })
        
        return data
    
    def _engineer_regime_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Engineering von Features für Regime-Erkennung"""
        try:
            # Preis-Trends über verschiedene Zeiträume
            data['price_trend_5'] = data['close'].pct_change(5).rolling(5).mean()
            data['price_trend_15'] = data['close'].pct_change(15).rolling(5).mean()
            data['price_trend_60'] = data['close'].pct_change(60).rolling(10).mean()
            
            # Volatilitäts-Maße
            data['volatility_5'] = data['close'].pct_change().rolling(5).std()
            data['volatility_15'] = data['close'].pct_change().rolling(15).std()
            data['volatility_60'] = data['close'].pct_change().rolling(60).std()
            
            # Volume Trend
            data['volume_ma'] = data['volume'].rolling(20).mean()
            data['volume_trend'] = (data['volume'] / data['volume_ma'] - 1).fillna(0)
            
            # Momentum Strength
            data['momentum_5'] = data['close'].pct_change(5)
            data['momentum_15'] = data['close'].pct_change(15)
            data['momentum_strength'] = (abs(data['momentum_5']) + abs(data['momentum_15'])) / 2
            
            # Trend Consistency (wie konstant ist der Trend)
            price_changes = data['close'].pct_change()
            data['trend_consistency'] = price_changes.rolling(20).apply(
                lambda x: len(x[x > 0]) / len(x) if len(x) > 0 else 0.5
            )
            
            # Support/Resistance Strength (vereinfacht)
            data['price_position'] = (data['close'] - data['low'].rolling(50).min()) / (
                data['high'].rolling(50).max() - data['low'].rolling(50).min()
            )
            data['support_resistance_strength'] = abs(data['price_position'] - 0.5)
            
            # Breakout Probability
            data['volatility_expansion'] = data['volatility_15'] / data['volatility_60']
            data['breakout_probability'] = np.where(data['volatility_expansion'] > 1.5, 1, 0)
            
            # NaN-Werte füllen
            for feature in self.regime_features:
                if feature in data.columns:
                    data[feature] = data[feature].fillna(0)
            
            return data
            
        except Exception as e:
            print(f"❌ Regime Feature Engineering Fehler: {e}")
            return data
    
    def _classify_historical_regimes(self, data: pd.DataFrame) -> pd.DataFrame:
        """Klassifiziert historische Daten in Regime"""
        try:
            # Regime-Klassifikation basierend auf Trend und Volatilität
            conditions = []
            
            # Bullish: Aufwärtstrend + moderate Volatilität
            bullish = (
                (data['price_trend_15'] > 0.0002) & 
                (data['trend_consistency'] > 0.6) &
                (data['volatility_15'] < data['volatility_15'].quantile(0.8))
            )
            
            # Bearish: Abwärtstrend + moderate Volatilität
            bearish = (
                (data['price_trend_15'] < -0.0002) & 
                (data['trend_consistency'] < 0.4) &
                (data['volatility_15'] < data['volatility_15'].quantile(0.8))
            )
            
            # High Volatility: Unabhängig von Trend-Richtung
            high_vol = data['volatility_15'] > data['volatility_15'].quantile(0.8)
            
            # Sideways: Kein klarer Trend + niedrige Volatilität
            sideways = (
                (abs(data['price_trend_15']) <= 0.0002) &
                (data['volatility_15'] <= data['volatility_15'].quantile(0.6))
            )
            
            # Regime zuweisen
            data['regime'] = 'NEUTRAL'
            data.loc[bullish, 'regime'] = 'BULLISH'
            data.loc[bearish, 'regime'] = 'BEARISH'
            data.loc[sideways, 'regime'] = 'SIDEWAYS'
            data.loc[high_vol, 'regime'] = 'HIGH_VOLATILITY'
            
            # Volatilitäts-Regime
            vol_threshold_low = data['volatility_15'].quantile(0.33)
            vol_threshold_high = data['volatility_15'].quantile(0.67)
            
            data['volatility_regime'] = 'MEDIUM'
            data.loc[data['volatility_15'] <= vol_threshold_low, 'volatility_regime'] = 'LOW'
            data.loc[data['volatility_15'] >= vol_threshold_high, 'volatility_regime'] = 'HIGH'
            
            return data
            
        except Exception as e:
            print(f"❌ Regime Klassifikation Fehler: {e}")
            return data
    
    def train_regime_models(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Trainiert ML-Modelle für Regime-Erkennung
        """
        print("🧠 Trainiere Regime-Erkennungs-Modelle...")
        
        try:
            if len(data) < 100:
                print("⚠️ Nicht genügend Daten für Regime-Training")
                return {}
            
            # Features vorbereiten
            feature_cols = [col for col in self.regime_features if col in data.columns]
            X = data[feature_cols].fillna(0)
            
            # Targets
            y_regime = data['regime']
            y_volatility = data['volatility_regime']
            
            # Nur Daten mit gültigen Labels verwenden
            valid_idx = (y_regime != 'NEUTRAL') & (X.notna().all(axis=1))
            X_valid = X[valid_idx]
            y_regime_valid = y_regime[valid_idx]
            y_volatility_valid = y_volatility[valid_idx]
            
            if len(X_valid) < 50:
                print("⚠️ Nicht genügend gültige Daten für Training")
                return {}
            
            # Scaling
            X_scaled = self.scaler.fit_transform(X_valid)
            
            # 1. Regime Classifier (Bullish/Bearish/Sideways)
            regime_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            regime_model.fit(X_scaled, y_regime_valid)
            
            # 2. Volatility Detector
            volatility_model = RandomForestClassifier(
                n_estimators=50,
                max_depth=8,
                random_state=42
            )
            volatility_model.fit(X_scaled, y_volatility_valid)
            
            # 3. Anomaly Detector
            anomaly_model = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            anomaly_model.fit(X_scaled)
            
            # Feature Importance
            feature_importance = dict(zip(feature_cols, regime_model.feature_importances_))
            top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
            
            print("✅ Regime-Modelle trainiert:")
            print(f"   - Regime Classifier: {len(set(y_regime_valid))} Klassen")
            print(f"   - Volatility Detector: {len(set(y_volatility_valid))} Klassen")
            print(f"   - Anomaly Detector: Isolation Forest")
            print("   - Top Features:")
            for feature, importance in top_features:
                print(f"     {feature}: {importance:.3f}")
            
            # Modelle speichern
            self.regime_classifier = regime_model
            self.volatility_detector = volatility_model
            self.anomaly_detector = anomaly_model
            
            # Auf Disk speichern
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            regime_path = os.path.join(self.models_dir, f'regime_classifier_{timestamp}.joblib')
            volatility_path = os.path.join(self.models_dir, f'volatility_detector_{timestamp}.joblib')
            anomaly_path = os.path.join(self.models_dir, f'anomaly_detector_{timestamp}.joblib')
            scaler_path = os.path.join(self.models_dir, f'regime_scaler_{timestamp}.joblib')
            
            joblib.dump(regime_model, regime_path)
            joblib.dump(volatility_model, volatility_path)
            joblib.dump(anomaly_model, anomaly_path)
            joblib.dump(self.scaler, scaler_path)
            
            results = {
                'regime_model': regime_model,
                'volatility_model': volatility_model,
                'anomaly_model': anomaly_model,
                'scaler': self.scaler,
                'feature_importance': feature_importance,
                'regime_path': regime_path,
                'volatility_path': volatility_path,
                'anomaly_path': anomaly_path,
                'scaler_path': scaler_path
            }
            
            return results
            
        except Exception as e:
            print(f"❌ Regime Model Training Fehler: {e}")
            return {}
    
    def detect_current_regime(self, symbol: str = "EURUSD") -> Dict[str, Any]:
        """
        Erkennt aktuelles Market Regime
        """
        try:
            if not self.regime_classifier:
                print("⚠️ Regime-Modelle nicht trainiert")
                return self._get_default_regime()
            
            # Aktuelle Marktdaten holen (simuliert)
            current_data = self._get_current_market_features(symbol)
            
            if current_data is None:
                print("⚠️ Keine aktuellen Marktdaten verfügbar")
                return self._get_default_regime()
            
            # Features für Prediction vorbereiten
            X = np.array(current_data).reshape(1, -1)
            X_scaled = self.scaler.transform(X)
            
            # Regime Prediction
            regime_pred = self.regime_classifier.predict(X_scaled)[0]
            regime_proba = self.regime_classifier.predict_proba(X_scaled)[0]
            regime_confidence = max(regime_proba)
            
            # Volatility Prediction
            volatility_pred = self.volatility_detector.predict(X_scaled)[0]
            volatility_proba = self.volatility_detector.predict_proba(X_scaled)[0]
            
            # Anomaly Detection
            anomaly_score = self.anomaly_detector.decision_function(X_scaled)[0]
            is_anomaly = self.anomaly_detector.predict(X_scaled)[0] == -1
            
            # Update internal state
            self.current_regime = regime_pred
            self.current_volatility = volatility_pred
            self.regime_confidence = regime_confidence
            self.last_update = datetime.now()
            
            result = {
                'symbol': symbol,
                'regime': regime_pred,
                'regime_confidence': regime_confidence,
                'volatility_regime': volatility_pred,
                'volatility_confidence': max(volatility_proba),
                'anomaly_score': anomaly_score,
                'is_anomaly': is_anomaly,
                'timestamp': self.last_update,
                'features': dict(zip(self.regime_features, current_data))
            }
            
            print(f"🔮 Regime Detection: {regime_pred} ({regime_confidence:.2f}) | "
                  f"Volatility: {volatility_pred} | Anomaly: {is_anomaly}")
            
            return result
            
        except Exception as e:
            print(f"❌ Regime Detection Fehler: {e}")
            return self._get_default_regime()
    
    def _get_current_market_features(self, symbol: str) -> Optional[List[float]]:
        """Holt aktuelle Markt-Features (simuliert für Demo)"""
        try:
            # In echter Implementierung würden hier MT5-Daten verwendet
            # Für Demo simulieren wir aktuelle Features
            np.random.seed(int(datetime.now().timestamp()) % 1000)
            
            features = []
            
            # Preis-Trends (simuliert)
            features.append(np.random.normal(0, 0.0003))  # price_trend_5
            features.append(np.random.normal(0, 0.0002))  # price_trend_15
            features.append(np.random.normal(0, 0.0001))  # price_trend_60
            
            # Volatilität
            features.append(np.random.uniform(0.0005, 0.002))  # volatility_5
            features.append(np.random.uniform(0.001, 0.003))   # volatility_15
            features.append(np.random.uniform(0.002, 0.004))   # volatility_60
            
            # Volume und Momentum
            features.append(np.random.uniform(-0.5, 0.5))      # volume_trend
            features.append(np.random.uniform(0, 0.002))       # momentum_strength
            features.append(np.random.uniform(0.3, 0.7))       # trend_consistency
            features.append(np.random.uniform(0, 0.5))         # support_resistance_strength
            features.append(np.random.choice([0, 1], p=[0.9, 0.1]))  # breakout_probability
            
            return features
            
        except Exception as e:
            print(f"❌ Current Market Features Fehler: {e}")
            return None
    
    def _get_default_regime(self) -> Dict[str, Any]:
        """Standard-Regime wenn Detection fehlschlägt"""
        return {
            'symbol': 'UNKNOWN',
            'regime': 'NEUTRAL',
            'regime_confidence': 0.5,
            'volatility_regime': 'MEDIUM',
            'volatility_confidence': 0.5,
            'anomaly_score': 0.0,
            'is_anomaly': False,
            'timestamp': datetime.now(),
            'features': {}
        }
    
    def get_regime_trading_recommendations(self, current_regime: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generiert Trading-Empfehlungen basierend auf aktuellem Regime
        """
        regime = current_regime['regime']
        volatility = current_regime['volatility_regime']
        confidence = current_regime['regime_confidence']
        
        recommendations = {
            'regime': regime,
            'volatility': volatility,
            'confidence': confidence,
            'trading_style': 'NEUTRAL',
            'risk_adjustment': 1.0,
            'position_size_multiplier': 1.0,
            'preferred_strategies': [],
            'avoid_strategies': [],
            'max_positions': 3
        }
        
        # Regime-spezifische Empfehlungen
        if regime == 'BULLISH' and confidence > 0.7:
            recommendations.update({
                'trading_style': 'TREND_FOLLOWING',
                'risk_adjustment': 1.2,
                'position_size_multiplier': 1.3,
                'preferred_strategies': ['BUY_MOMENTUM', 'BREAKOUT_LONG'],
                'avoid_strategies': ['MEAN_REVERSION', 'SHORT_BIAS'],
                'max_positions': 4
            })
            
        elif regime == 'BEARISH' and confidence > 0.7:
            recommendations.update({
                'trading_style': 'TREND_FOLLOWING',
                'risk_adjustment': 1.2,
                'position_size_multiplier': 1.3,
                'preferred_strategies': ['SELL_MOMENTUM', 'BREAKOUT_SHORT'],
                'avoid_strategies': ['MEAN_REVERSION', 'LONG_BIAS'],
                'max_positions': 4
            })
            
        elif regime == 'SIDEWAYS':
            recommendations.update({
                'trading_style': 'MEAN_REVERSION',
                'risk_adjustment': 0.8,
                'position_size_multiplier': 0.8,
                'preferred_strategies': ['RANGE_TRADING', 'SUPPORT_RESISTANCE'],
                'avoid_strategies': ['MOMENTUM', 'BREAKOUT'],
                'max_positions': 2
            })
            
        elif regime == 'HIGH_VOLATILITY':
            recommendations.update({
                'trading_style': 'SCALPING',
                'risk_adjustment': 0.5,
                'position_size_multiplier': 0.6,
                'preferred_strategies': ['QUICK_SCALP', 'VOLATILITY_BREAKOUT'],
                'avoid_strategies': ['SWING_TRADING', 'POSITION_TRADING'],
                'max_positions': 5
            })
        
        # Volatilitäts-Anpassungen
        if volatility == 'HIGH':
            recommendations['risk_adjustment'] *= 0.7
            recommendations['position_size_multiplier'] *= 0.8
        elif volatility == 'LOW':
            recommendations['risk_adjustment'] *= 1.2
            recommendations['position_size_multiplier'] *= 1.1
        
        # Anomaly-Anpassungen
        if current_regime.get('is_anomaly', False):
            recommendations['risk_adjustment'] *= 0.5
            recommendations['position_size_multiplier'] *= 0.5
            recommendations['max_positions'] = 1
            print("⚠️ Anomalie erkannt - Risiko reduziert")
        
        return recommendations
    
    def run_regime_monitoring(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Startet kontinuierliches Regime-Monitoring
        """
        if symbols is None:
            symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        
        print(f"🔍 Starte Regime-Monitoring für {len(symbols)} Symbole")
        
        monitoring_results = {}
        
        for symbol in symbols:
            try:
                # Regime Detection
                regime_info = self.detect_current_regime(symbol)
                
                # Trading Recommendations
                recommendations = self.get_regime_trading_recommendations(regime_info)
                
                monitoring_results[symbol] = {
                    'regime_info': regime_info,
                    'recommendations': recommendations,
                    'last_update': datetime.now()
                }
                
                print(f"   {symbol}: {regime_info['regime']} | Risk: {recommendations['risk_adjustment']:.1f}x")
                
            except Exception as e:
                print(f"❌ Monitoring Fehler für {symbol}: {e}")
                monitoring_results[symbol] = {
                    'error': str(e),
                    'last_update': datetime.now()
                }
        
        # Gesamtmarkt-Assessment
        regimes = [result['regime_info']['regime'] for result in monitoring_results.values() 
                  if 'regime_info' in result]
        
        if regimes:
            dominant_regime = max(set(regimes), key=regimes.count)
            regime_consensus = regimes.count(dominant_regime) / len(regimes)
            
            print(f"📊 Markt-Konsensus: {dominant_regime} ({regime_consensus:.1%})")
            
            monitoring_results['market_consensus'] = {
                'dominant_regime': dominant_regime,
                'consensus_strength': regime_consensus,
                'total_symbols': len(symbols),
                'successful_analysis': len(regimes)
            }
        
        return monitoring_results

# Demo-Ausführung
if __name__ == "__main__":
    print("🔮 MARKET REGIME DETECTOR")
    print("=" * 50)
    
    detector = MarketRegimeDetector()
    
    # 1. Marktdaten analysieren
    market_data = detector.analyze_market_data_for_regimes("EURUSD", 200)
    
    if not market_data.empty:
        # 2. Modelle trainieren
        models = detector.train_regime_models(market_data)
        
        if models:
            # 3. Aktuelles Regime erkennen
            current_regime = detector.detect_current_regime("EURUSD")
            
            # 4. Trading-Empfehlungen
            recommendations = detector.get_regime_trading_recommendations(current_regime)
            
            print(f"\n🎯 Trading-Empfehlungen:")
            print(f"   Style: {recommendations['trading_style']}")
            print(f"   Risk Adjustment: {recommendations['risk_adjustment']:.1f}x")
            print(f"   Position Size: {recommendations['position_size_multiplier']:.1f}x")
            print(f"   Max Positions: {recommendations['max_positions']}")
            
            # 5. Multi-Symbol Monitoring
            monitoring = detector.run_regime_monitoring(['EURUSD', 'GBPUSD', 'USDJPY'])
    
    print("\n✅ Market Regime Detector bereit für Integration!")

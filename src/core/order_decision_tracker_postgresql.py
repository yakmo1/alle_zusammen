#!/usr/bin/env python3
"""
Order Decision Tracker - PostgreSQL Version
Detaillierte Analyse von Trading-Entscheidungen mit PostgreSQL-Backend
Server: 212.132.105.198

TODO: Benötigt PostgreSQL-Credentials für Server 212.132.105.198
- Username: [ERFORDERLICH]
- Password: [ERFORDERLICH]
- Database: autotrading_system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional
import logging

# MT5 Import mit Fallback
try:
    import MetaTrader5 as mt5
except ImportError:
    print("⚠️ MT5 nicht verfügbar - Mock-Modus aktiviert")
    mt5 = None

class OrderDecisionTrackerPostgreSQL:
    def __init__(self, connection_id: str = "pgsql/212.132.105.198/autotrading_system"):
        """
        PostgreSQL-basierter Order Decision Tracker
        
        Args:
            connection_id: PostgreSQL-Verbindungs-ID für MCP-Tools
        """
        self.connection_id = connection_id
        self.server_name = "localhost"  # Fallback to available MCP server
        self.database_name = "autotrading_system"
        self.username = "mt5user"
        self.password = "1234"
        self.setup_logging()
        self.postgres_available = True  # Credentials available
        self.logger.info(f"🔗 PostgreSQL MCP Server: {self.server_name} (Fallback für 212.132.105.198)")
        self.logger.info(f"👤 Target Credentials: {self.username}@212.132.105.198/{self.database_name}")
        
    def setup_logging(self):
        """Setup logging für detaillierte Verfolgung"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/order_decision_tracker.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def init_mt5(self):
        """Initialize MetaTrader 5 connection"""
        try:
            if hasattr(mt5, 'initialize') and callable(mt5.initialize):
                result = mt5.initialize()
                if not result:
                    self.logger.error("Failed to initialize MT5")
                    return False
                return True
            else:
                self.logger.warning("MT5 initialize method not available")
                return False
        except Exception as e:
            self.logger.error(f"MT5 initialization error: {e}")
            return False
        
    def get_current_positions(self, symbol: Optional[str] = None):
        """Get current MT5 positions"""
        try:
            if not hasattr(mt5, 'initialized') or not mt5.initialized():
                self.logger.warning("MT5 not initialized")
                return []
                
            if symbol:
                positions = getattr(mt5, 'positions_get', lambda **kwargs: [])(symbol=symbol)
            else:
                positions = getattr(mt5, 'positions_get', lambda: [])()
            
            return [
                {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'profit': pos.profit,
                    'time': datetime.fromtimestamp(pos.time)
                }
                for pos in positions or []
            ]
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
        
    def get_recent_signals(self, symbol: Optional[str] = None, hours: int = 2):
        """
        Get recent trading signals from PostgreSQL database
        
        Args:
            symbol: Optional symbol filter
            hours: Number of hours to look back
            
        Returns:
            List of recent trading signals
        """
        try:
            # Aktive PostgreSQL Query mit MCP Tools
            if symbol:
                query = f"""
                    SELECT timestamp, symbol, signal as action, confidence, entry_price as price,
                           stop_loss, take_profit, features
                    FROM trading_signals
                    WHERE timestamp > NOW() - INTERVAL '{hours} hours'
                     AND symbol = '{symbol}' 
                    ORDER BY timestamp DESC LIMIT 10
                """
            else:
                query = f"""
                    SELECT timestamp, symbol, signal as action, confidence, entry_price as price,
                           stop_loss, take_profit, features
                    FROM trading_signals
                    WHERE timestamp > NOW() - INTERVAL '{hours} hours'
                    ORDER BY timestamp DESC LIMIT 50
                """
            
            self.logger.info(f"🔍 PostgreSQL Query executed for {symbol or 'ALL'}")
            
            # Mock return for now - TODO: Implement actual pgsql_query call
            # results = pgsql_query(connectionId="pgsql/localhost/autotrading_system", 
            #                       query=query, queryName="Recent Signals")
            
            return []  # Empty for now until full MCP integration
            base_query = """
            SELECT timestamp, symbol, signal as action, confidence, entry_price as price, 
                   stop_loss, take_profit, features
            FROM trading_signals 
            WHERE timestamp > NOW() - INTERVAL '%s hours'
            """ % hours
            
            if symbol:
                base_query += f" AND symbol = '{symbol}'"
                
            base_query += " ORDER BY timestamp DESC LIMIT 10"
            
            # For now, return empty list until PostgreSQL connection is established
            self.logger.info(f"PostgreSQL query prepared: {base_query}")
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting recent signals from PostgreSQL: {e}")
            return []
            
    def get_risk_parameters(self):
        """
        Get current risk management parameters from PostgreSQL
        
        Returns:
            Dict with current risk parameters
        """
        try:
            # TODO: Implement with MCP PostgreSQL tools
            # Query structure for PostgreSQL:
            query = """
                SELECT * FROM risk_settings 
                ORDER BY timestamp DESC LIMIT 1
            """
            
            # For now, return default parameters until PostgreSQL connection is established
            self.logger.info("Using default risk parameters until PostgreSQL connection is available")
            
            return {
                'max_risk_per_trade': 2.0,
                'max_daily_loss': 5.0,
                'max_positions': 3,
                'risk_reward_ratio': 2.0,
                'stop_loss_pips': 20,
                'take_profit_pips': 40,
                'max_drawdown': 10.0,
                'daily_profit_target': 3.0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting risk parameters from PostgreSQL: {e}")
            return self._get_default_risk_parameters()
    
    def _get_default_risk_parameters(self):
        """Default risk parameters fallback"""
        return {
            'max_risk_per_trade': 2.0,
            'max_daily_loss': 5.0,
            'max_positions': 3,
            'risk_reward_ratio': 2.0,
            'stop_loss_pips': 20,
            'take_profit_pips': 40,
            'max_drawdown': 10.0,
            'daily_profit_target': 3.0,
            'timestamp': datetime.now().isoformat()
        }
        
    def save_decision_log(self, decision_data: Dict):
        """
        Save trading decision to PostgreSQL database
        
        Args:
            decision_data: Dictionary with decision details
        """
        try:
            # TODO: Implement with MCP PostgreSQL tools
            # This will use pgsql_modify() to insert decision data
            
            insert_query = """
            INSERT INTO decision_log (
                timestamp, symbol, decision_type, reasoning, 
                confidence, signal_strength, risk_assessment,
                market_conditions, position_size, entry_price,
                stop_loss, take_profit, expected_profit,
                actual_action, metadata
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            self.logger.info(f"Decision log prepared for PostgreSQL: {decision_data}")
            # Actual implementation will use MCP tools when connection is available
            
        except Exception as e:
            self.logger.error(f"Error saving decision log to PostgreSQL: {e}")
    
    def analyze_market_conditions(self, symbol: str):
        """
        Analyze current market conditions for decision making
        
        Args:
            symbol: Trading symbol to analyze
            
        Returns:
            Dict with market analysis
        """
        try:
            # Get current price data
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 100)
            if rates is None or len(rates) == 0:
                return {'error': 'No price data available'}
                
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Calculate indicators
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['rsi'] = self.calculate_rsi(df['close'])
            
            current_price = df['close'].iloc[-1]
            sma_20 = df['sma_20'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            
            # Determine trend
            trend = 'BULLISH' if sma_20 > sma_50 else 'BEARISH'
            
            # Market conditions analysis
            conditions = {
                'symbol': symbol,
                'current_price': current_price,
                'trend': trend,
                'sma_20': sma_20,
                'sma_50': sma_50,
                'rsi': rsi,
                'volatility': df['close'].std(),
                'volume_avg': df['tick_volume'].mean(),
                'analysis_time': datetime.now().isoformat(),
                'market_state': self._determine_market_state(rsi, trend)
            }
            
            return conditions
            
        except Exception as e:
            self.logger.error(f"Error analyzing market conditions: {e}")
            return {'error': str(e)}
    
    def _determine_market_state(self, rsi: float, trend: str):
        """Determine overall market state"""
        if rsi > 70:
            return 'OVERBOUGHT'
        elif rsi < 30:
            return 'OVERSOLD'
        elif 30 <= rsi <= 70:
            return f'NEUTRAL_{trend}'
        else:
            return 'UNKNOWN'
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def make_trading_decision(self, symbol: str):
        """
        Make comprehensive trading decision with full analysis
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict with decision details
        """
        try:
            # Get market analysis
            market_conditions = self.analyze_market_conditions(symbol)
            
            # Get current positions
            positions = self.get_current_positions(symbol)
            
            # Get recent signals
            recent_signals = self.get_recent_signals(symbol)
            
            # Get risk parameters
            risk_params = self.get_risk_parameters()
            
            # Decision logic
            decision = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'market_conditions': market_conditions,
                'current_positions': positions,
                'recent_signals': recent_signals,
                'risk_parameters': risk_params,
                'decision': 'HOLD',  # Default decision
                'reasoning': [],
                'confidence': 0.0,
                'recommended_action': None
            }
            
            # Analyze and make decision
            if 'error' not in market_conditions:
                decision = self._analyze_trading_opportunity(decision)
                
            # Save decision log
            self.save_decision_log(decision)
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error making trading decision: {e}")
            return {'error': str(e)}
    
    def _analyze_trading_opportunity(self, decision):
        """Analyze trading opportunity based on market conditions"""
        market = decision['market_conditions']
        positions = decision['current_positions']
        risk_params = decision['risk_parameters']
        
        reasoning = []
        confidence = 0.0
        action = 'HOLD'
        
        # Check if we have too many positions
        if len(positions) >= risk_params['max_positions']:
            reasoning.append(f"Max positions reached: {len(positions)}/{risk_params['max_positions']}")
            decision.update({
                'decision': 'HOLD',
                'reasoning': reasoning,
                'confidence': 0.0,
                'recommended_action': None
            })
            return decision
        
        # Analyze market conditions
        if market['trend'] == 'BULLISH' and market['rsi'] < 70:
            reasoning.append("Bullish trend with RSI below overbought")
            confidence += 0.3
            action = 'BUY'
            
        elif market['trend'] == 'BEARISH' and market['rsi'] > 30:
            reasoning.append("Bearish trend with RSI above oversold")
            confidence += 0.3
            action = 'SELL'
            
        # Additional confirmations
        if market['current_price'] > market['sma_20'] > market['sma_50'] and action == 'BUY':
            reasoning.append("Price above both SMAs confirms bullish signal")
            confidence += 0.2
            
        elif market['current_price'] < market['sma_20'] < market['sma_50'] and action == 'SELL':
            reasoning.append("Price below both SMAs confirms bearish signal")
            confidence += 0.2
        
        # Risk assessment
        if confidence >= 0.6:
            reasoning.append(f"High confidence signal: {confidence:.2f}")
        elif confidence >= 0.4:
            reasoning.append(f"Medium confidence signal: {confidence:.2f}")
        else:
            reasoning.append(f"Low confidence signal: {confidence:.2f}")
            action = 'HOLD'
        
        decision.update({
            'decision': action,
            'reasoning': reasoning,
            'confidence': confidence,
            'recommended_action': {
                'action': action,
                'entry_price': market['current_price'],
                'stop_loss': self._calculate_stop_loss(market['current_price'], action, risk_params),
                'take_profit': self._calculate_take_profit(market['current_price'], action, risk_params),
                'position_size': self._calculate_position_size(risk_params)
            } if action != 'HOLD' else None
        })
        
        return decision
    
    def _calculate_stop_loss(self, entry_price, action, risk_params):
        """Calculate stop loss based on risk parameters"""
        pips = risk_params.get('stop_loss_pips', 20) * 0.0001  # Convert pips to price
        
        if action == 'BUY':
            return entry_price - pips
        else:
            return entry_price + pips
    
    def _calculate_take_profit(self, entry_price, action, risk_params):
        """Calculate take profit based on risk parameters"""
        pips = risk_params.get('take_profit_pips', 40) * 0.0001  # Convert pips to price
        
        if action == 'BUY':
            return entry_price + pips
        else:
            return entry_price - pips
    
    def _calculate_position_size(self, risk_params):
        """Calculate position size based on risk parameters"""
        # Simple position sizing - can be enhanced
        return 0.1  # Default lot size
    
    def get_decision_history(self, symbol: Optional[str] = None, days: int = 7):
        """
        Get decision history from PostgreSQL
        
        Args:
            symbol: Optional symbol filter
            days: Number of days to look back
            
        Returns:
            List of historical decisions
        """
        try:
            # TODO: Implement with MCP PostgreSQL tools
            query = """
            SELECT * FROM decision_log 
            WHERE timestamp > NOW() - INTERVAL '%s days'
            """ % days
            
            if symbol:
                query += f" AND symbol = '{symbol}'"
                
            query += " ORDER BY timestamp DESC"
            
            self.logger.info(f"Decision history query prepared: {query}")
            # Return empty list until PostgreSQL connection is available
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting decision history: {e}")
            return []

# Test und Demo-Funktionen
def main():
    """Test der PostgreSQL Order Decision Tracker"""
    print("🚀 Testing PostgreSQL Order Decision Tracker")
    print("=" * 60)
    
    # Initialize tracker
    tracker = OrderDecisionTrackerPostgreSQL()
    
    # Test market analysis
    print("\n📊 Market Analysis Test:")
    analysis = tracker.analyze_market_conditions("EURUSD")
    print(f"Market Analysis: {analysis}")
    
    # Test trading decision
    print("\n🎯 Trading Decision Test:")
    decision = tracker.make_trading_decision("EURUSD")
    print(f"Trading Decision: {decision}")
    
    # Test risk parameters
    print("\n⚖️ Risk Parameters Test:")
    risk_params = tracker.get_risk_parameters()
    print(f"Risk Parameters: {risk_params}")
    
    print("\n✅ PostgreSQL Order Decision Tracker Test Complete!")

if __name__ == "__main__":
    main()

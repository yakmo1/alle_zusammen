#!/usr/bin/env python3
"""
Order Decision Tracker - Detaillierte Analyse von Trading-Entscheidungen
Zeigt genau warum ein Trade ausgelöst wurde oder nicht
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import MetaTrader5 as mt5
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional
import logging

class OrderDecisionTracker:
    def __init__(self, db_path: str = "trading_robot.db"):
        self.db_path = db_path
        self.setup_logging()
        self.init_mt5()
        
    def setup_logging(self):
        """Setup logging für detaillierte Verfolgung"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('order_decisions.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def init_mt5(self):
        """Initialize MetaTrader 5"""
        if not mt5.initialize():
            self.logger.error("MT5 initialization failed")
            return False
        self.logger.info("MT5 initialized successfully")
        return True
        
    def get_account_info(self):
        """Get current account information"""
        account_info = mt5.account_info()
        if account_info:
            return {
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level if account_info.margin > 0 else float('inf'),
                'currency': account_info.currency
            }
        return None
        
    def get_current_positions(self, symbol: str = None):
        """Get current open positions"""
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
            
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
        
    def get_recent_signals(self, symbol: str = None, hours: int = 2):
        """Get recent trading signals from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = """
            SELECT timestamp, symbol, signal as action, confidence, entry_price as price, 
                   stop_loss, take_profit, features
            FROM trading_signals 
            WHERE timestamp > datetime('now', '-{} hours')
            """.format(hours)
            
            if symbol:
                query += f" AND symbol = '{symbol}'"
                
            query += " ORDER BY timestamp DESC LIMIT 10"  # Limit to 10 most recent signals
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Convert features JSON string to dict for better handling
            if not df.empty:
                records = df.to_dict('records')
                for record in records:
                    try:
                        if record.get('features'):
                            record['features'] = json.loads(record['features'])
                    except:
                        record['features'] = {}
                return records
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting recent signals: {e}")
            return []
            
    def get_risk_parameters(self):
        """Get current risk management parameters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest risk settings
            cursor.execute("""
                SELECT * FROM risk_settings 
                ORDER BY timestamp DESC LIMIT 1
            """)
            
            risk_data = cursor.fetchone()
            conn.close()
            
            if risk_data:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, risk_data))
            else:
                # Default risk parameters
                return {
                    'max_risk_per_trade': 2.0,
                    'max_daily_loss': 5.0,
                    'max_positions': 3,
                    'min_confidence': 0.65,  # Decimal format (65%)
                    'max_correlation': 0.8
                }
                
        except Exception as e:
            self.logger.error(f"Error getting risk parameters: {e}")
            return {}
            
    def check_trading_conditions(self, symbol: str):
        """Check all trading conditions for a symbol"""
        conditions = {
            'symbol_tradeable': False,
            'market_open': False,
            'sufficient_margin': False,
            'position_limit_ok': False,
            'daily_loss_ok': False,
            'correlation_ok': False,
            'spread_acceptable': False,
            'details': {}
        }
        
        try:
            # Check if symbol is tradeable
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                conditions['symbol_tradeable'] = symbol_info.visible and symbol_info.trade_mode != 0
                conditions['details']['symbol_info'] = {
                    'visible': symbol_info.visible,
                    'trade_mode': symbol_info.trade_mode,
                    'spread': symbol_info.spread,
                    'min_lot': symbol_info.volume_min,
                    'max_lot': symbol_info.volume_max
                }
                
                # Check spread
                spread_points = symbol_info.spread
                max_spread = 20  # Maximum acceptable spread in points
                conditions['spread_acceptable'] = spread_points <= max_spread
                conditions['details']['spread'] = {
                    'current': spread_points,
                    'max_allowed': max_spread,
                    'acceptable': conditions['spread_acceptable']
                }
            
            # Check market hours
            market_info = mt5.symbol_info_tick(symbol)
            if market_info:
                conditions['market_open'] = market_info.time > 0
                conditions['details']['market_time'] = datetime.fromtimestamp(market_info.time)
            
            # Check account conditions
            account_info = self.get_account_info()
            if account_info:
                conditions['sufficient_margin'] = account_info['margin_level'] > 200
                conditions['details']['account'] = account_info
            
            # Check position limits
            current_positions = self.get_current_positions()
            risk_params = self.get_risk_parameters()
            
            max_positions = risk_params.get('max_positions', 3)
            conditions['position_limit_ok'] = len(current_positions) < max_positions
            conditions['details']['positions'] = {
                'current_count': len(current_positions),
                'max_allowed': max_positions,
                'positions': current_positions
            }
            
            # Check daily loss limit
            today_pnl = self.get_daily_pnl()
            max_daily_loss = risk_params.get('max_daily_loss', 5.0)
            daily_loss_percent = abs(today_pnl) / account_info['balance'] * 100 if account_info else 0
            
            conditions['daily_loss_ok'] = daily_loss_percent < max_daily_loss
            conditions['details']['daily_pnl'] = {
                'pnl_amount': today_pnl,
                'pnl_percent': daily_loss_percent,
                'max_loss_percent': max_daily_loss,
                'within_limit': conditions['daily_loss_ok']
            }
            
            # Check correlation with existing positions
            correlation_ok, correlation_details = self.check_correlation(symbol, current_positions)
            conditions['correlation_ok'] = correlation_ok
            conditions['details']['correlation'] = correlation_details
            
        except Exception as e:
            self.logger.error(f"Error checking trading conditions: {e}")
            conditions['details']['error'] = str(e)
            
        return conditions
        
    def get_daily_pnl(self):
        """Get today's P&L"""
        try:
            # Get today's date range
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            # Get today's closed trades
            deals = mt5.history_deals_get(today, tomorrow)
            if deals:
                return sum(deal.profit for deal in deals if deal.entry == 1)  # Only closing deals
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating daily P&L: {e}")
            return 0.0
            
    def check_correlation(self, symbol: str, current_positions: List[Dict]):
        """Check correlation with existing positions"""
        if not current_positions:
            return True, {'message': 'No existing positions'}
        
        # Simplified correlation check based on currency pairs
        base_currency = symbol[:3]
        quote_currency = symbol[3:6]
        
        correlated_positions = []
        for pos in current_positions:
            pos_base = pos['symbol'][:3]
            pos_quote = pos['symbol'][3:6]
            
            # Check if currencies overlap
            if (base_currency in [pos_base, pos_quote] or 
                quote_currency in [pos_base, pos_quote]):
                correlated_positions.append(pos)
        
        max_correlation = 0.8  # Max allowed correlation
        correlation_ratio = len(correlated_positions) / len(current_positions)
        
        return correlation_ratio <= max_correlation, {
            'correlated_positions': correlated_positions,
            'correlation_ratio': correlation_ratio,
            'max_allowed': max_correlation,
            'acceptable': correlation_ratio <= max_correlation
        }
        
    def analyze_signal_decision(self, symbol: str, signal_data: Dict):
        """Analyze why a signal led to a trade decision or not"""
        self.logger.info(f"Analyzing signal decision for {symbol}")
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'signal': signal_data,
            'trading_conditions': self.check_trading_conditions(symbol),
            'risk_parameters': self.get_risk_parameters(),
            'account_status': self.get_account_info(),
            'decision': 'PENDING',
            'decision_reasons': []
        }
        
        # Analyze decision logic
        conditions = analysis['trading_conditions']
        signal_confidence = signal_data.get('confidence', 0)
        min_confidence = analysis['risk_parameters'].get('min_confidence', 70)
        
        # Check each condition
        if not conditions['symbol_tradeable']:
            analysis['decision'] = 'REJECTED'
            analysis['decision_reasons'].append('Symbol not tradeable')
            
        elif not conditions['market_open']:
            analysis['decision'] = 'REJECTED'
            analysis['decision_reasons'].append('Market closed')
            
        elif signal_confidence < min_confidence:
            analysis['decision'] = 'REJECTED'
            analysis['decision_reasons'].append(f'Confidence {signal_confidence:.1%} < minimum {min_confidence:.1%}')
            
        elif not conditions['sufficient_margin']:
            analysis['decision'] = 'REJECTED'
            analysis['decision_reasons'].append('Insufficient margin')
            
        elif not conditions['position_limit_ok']:
            analysis['decision'] = 'REJECTED'
            analysis['decision_reasons'].append('Position limit exceeded')
            
        elif not conditions['daily_loss_ok']:
            analysis['decision'] = 'REJECTED'
            analysis['decision_reasons'].append('Daily loss limit exceeded')
            
        elif not conditions['correlation_ok']:
            analysis['decision'] = 'REJECTED'
            analysis['decision_reasons'].append('Correlation limit exceeded')
            
        elif not conditions['spread_acceptable']:
            analysis['decision'] = 'REJECTED'
            analysis['decision_reasons'].append('Spread too high')
            
        else:
            analysis['decision'] = 'APPROVED'
            analysis['decision_reasons'].append('All conditions met')
            
        return analysis
        
    def get_recent_decision_analysis(self, hours: int = 2):
        """Get analysis of recent signal decisions"""
        signals = self.get_recent_signals(hours=hours)
        analyses = []
        
        for signal in signals:
            analysis = self.analyze_signal_decision(signal['symbol'], signal)
            analyses.append(analysis)
            
        return analyses
        
    def print_decision_summary(self, symbol: str = None):
        """Print a formatted summary of recent decisions"""
        print("\n" + "="*80)
        print("🔍 ORDER DECISION TRACKER - DETAILED ANALYSIS")
        print("="*80)
        
        # Get recent signals
        signals = self.get_recent_signals(symbol=symbol, hours=2)
        
        if not signals:
            print("❌ No recent signals found")
            return
            
        for i, signal in enumerate(signals):
            print(f"\n📊 SIGNAL #{i+1} - {signal['symbol']}")
            print("-" * 50)
            
            # Analyze this signal
            analysis = self.analyze_signal_decision(signal['symbol'], signal)
            
            # Signal details
            print(f"⏰ Time: {signal['timestamp']}")
            print(f"📈 Action: {signal['action']}")
            print(f"🎯 Confidence: {signal['confidence']}%")
            print(f"💰 Price: {signal['price']}")
            print(f"📝 Reason: {signal.get('stop_loss', 'N/A')} SL / {signal.get('take_profit', 'N/A')} TP")
            
            # Decision result
            decision_emoji = "✅" if analysis['decision'] == 'APPROVED' else "❌"
            print(f"\n{decision_emoji} DECISION: {analysis['decision']}")
            
            # Decision reasons
            print("🔍 Decision Analysis:")
            for reason in analysis['decision_reasons']:
                print(f"   • {reason}")
                
            # Detailed conditions
            conditions = analysis['trading_conditions']
            print("\n📋 Trading Conditions Check:")
            
            condition_checks = [
                ('Symbol Tradeable', conditions['symbol_tradeable']),
                ('Market Open', conditions['market_open']),
                ('Sufficient Margin', conditions['sufficient_margin']),
                ('Position Limit OK', conditions['position_limit_ok']),
                ('Daily Loss OK', conditions['daily_loss_ok']),
                ('Correlation OK', conditions['correlation_ok']),
                ('Spread Acceptable', conditions['spread_acceptable'])
            ]
            
            for name, status in condition_checks:
                emoji = "✅" if status else "❌"
                print(f"   {emoji} {name}: {status}")
                
            # Additional details
            if 'details' in conditions:
                details = conditions['details']
                
                if 'spread' in details:
                    spread_info = details['spread']
                    print(f"\n📊 Spread Info:")
                    print(f"   Current: {spread_info['current']} points")
                    print(f"   Max Allowed: {spread_info['max_allowed']} points")
                    
                if 'positions' in details:
                    pos_info = details['positions']
                    print(f"\n🏪 Position Info:")
                    print(f"   Current Positions: {pos_info['current_count']}")
                    print(f"   Max Allowed: {pos_info['max_allowed']}")
                    
                    if pos_info['positions']:
                        print("   Open Positions:")
                        for pos in pos_info['positions']:
                            print(f"     • {pos['symbol']} {pos['type']} {pos['volume']} lots (Profit: {pos['profit']:.2f})")
                            
                if 'daily_pnl' in details:
                    pnl_info = details['daily_pnl']
                    print(f"\n💹 Daily P&L:")
                    print(f"   Amount: {pnl_info['pnl_amount']:.2f}")
                    print(f"   Percentage: {pnl_info['pnl_percent']:.2f}%")
                    print(f"   Max Loss: {pnl_info['max_loss_percent']:.2f}%")
                    
        print("\n" + "="*80)
        
    def save_analysis_to_file(self, filename: str = None):
        """Save detailed analysis to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"order_decision_analysis_{timestamp}.json"
            
        analyses = self.get_recent_decision_analysis(hours=24)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analyses, f, indent=2, ensure_ascii=False, default=str)
            
        self.logger.info(f"Analysis saved to {filename}")
        return filename

def main():
    """Main function for command line usage"""
    tracker = OrderDecisionTracker()
    
    print("🤖 Order Decision Tracker gestartet...")
    
    # Check if specific symbol was provided
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Print detailed analysis
    tracker.print_decision_summary(symbol)
    
    # Save to file
    filename = tracker.save_analysis_to_file()
    print(f"\n💾 Detaillierte Analyse gespeichert in: {filename}")

if __name__ == "__main__":
    main()

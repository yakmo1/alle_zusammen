"""
MetaTrader 5 Connector
Verbindung und Datenaustausch mit MT5
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time

class MT5ConnectorSimple:
    """Simple MT5 Connector - uses already running MT5 instance"""

    def __init__(self):
        self.connected = False

    def connect(self) -> bool:
        """Connect to already running MT5 instance"""
        try:
            # Just initialize - don't login
            initialized = mt5.initialize()

            if not initialized:
                error = mt5.last_error()
                logging.error(f"MT5 initialization failed: {error}")
                return False

            # Check if we have account info (means MT5 is logged in)
            account_info = mt5.account_info()
            if account_info is None:
                logging.error("MT5 is not logged in")
                mt5.shutdown()
                return False

            self.connected = True
            logging.info(f"MT5 connected to running instance: Account {account_info.login}")
            return True

        except Exception as e:
            logging.error(f"MT5 connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logging.info("MT5 disconnected")

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.connected:
            return {}

        try:
            account_info = mt5.account_info()
            if account_info is None:
                logging.error("No account information available")
                return {}

            return {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'profit': account_info.profit,
                'currency': account_info.currency,
                'server': account_info.server,
                'leverage': account_info.leverage
            }
        except Exception as e:
            logging.error(f"Error getting account info: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        if not self.connected:
            return []

        try:
            positions = mt5.positions_get()
            if positions is None:
                return []

            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'time': pos.time
                })

            return result

        except Exception as e:
            logging.error(f"Error getting positions: {e}")
            return []

class MT5Connector:
    def __init__(self, login: int, password: str, server: str, path: str = ""):
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.connected = False
        
    def connect(self) -> bool:
        """Verbindung zu MT5 herstellen"""
        try:
            # MT5 initialisieren
            if self.path:
                initialized = mt5.initialize(path=self.path)
            else:
                initialized = mt5.initialize()
                
            if not initialized:
                logging.error(f"MT5 Initialisierung fehlgeschlagen: {mt5.last_error()}")
                return False
            
            # Login durchführen
            authorized = mt5.login(self.login, password=self.password, server=self.server)
            if not authorized:
                logging.error(f"MT5 Login fehlgeschlagen: {mt5.last_error()}")
                return False
            
            self.connected = True
            logging.info(f"MT5 Verbindung erfolgreich: {mt5.account_info()}")
            return True
            
        except Exception as e:
            logging.error(f"MT5 Verbindungsfehler: {e}")
            return False
    
    def disconnect(self):
        """MT5 Verbindung trennen"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logging.info("MT5 Verbindung getrennt")
    
    def get_account_info(self) -> Dict[str, Any]:
        """Account-Informationen abrufen"""
        if not self.connected:
            return {}
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                logging.error("Keine Account-Informationen verfügbar")
                return {}
            
            return {
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'profit': account_info.profit,
                'currency': account_info.currency,
                'server': account_info.server,
                'leverage': account_info.leverage
            }
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Account-Info: {e}")
            return {}
    
    def get_symbols(self) -> List[str]:
        """Verfügbare Symbole abrufen"""
        if not self.connected:
            return []
        
        try:
            symbols = mt5.symbols_get()
            if symbols is None:
                return []
            
            return [symbol.name for symbol in symbols if symbol.visible]
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Symbole: {e}")
            return []
    
    def get_rates(self, symbol: str, timeframe: int, count: int = 1000) -> pd.DataFrame:
        """Kursdaten abrufen"""
        if not self.connected:
            return pd.DataFrame()
        
        try:
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
            if rates is None:
                logging.error(f"Keine Kursdaten für {symbol} verfügbar")
                return pd.DataFrame()
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
            
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Kursdaten für {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Dict[str, float]:
        """Aktueller Preis eines Symbols"""
        if not self.connected:
            return {}
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return {}
            
            return {
                'bid': tick.bid,
                'ask': tick.ask,
                'spread': tick.ask - tick.bid,
                'time': datetime.fromtimestamp(tick.time)
            }
        except Exception as e:
            logging.error(f"Fehler beim Abrufen des aktuellen Preises für {symbol}: {e}")
            return {}
    
    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: float = 0, sl: float = 0, tp: float = 0, 
                   comment: str = "", magic: int = 0) -> Dict[str, Any]:
        """Order platzieren"""
        if not self.connected:
            return {'success': False, 'error': 'Nicht mit MT5 verbunden'}
        
        try:
            # Order-Type konvertieren
            if order_type.upper() == 'BUY':
                order_type_mt5 = mt5.ORDER_TYPE_BUY
                action = mt5.TRADE_ACTION_DEAL
                if price == 0:
                    price = mt5.symbol_info_tick(symbol).ask
            elif order_type.upper() == 'SELL':
                order_type_mt5 = mt5.ORDER_TYPE_SELL
                action = mt5.TRADE_ACTION_DEAL
                if price == 0:
                    price = mt5.symbol_info_tick(symbol).bid
            else:
                return {'success': False, 'error': 'Ungültiger Order-Type'}
            
            # Request zusammenstellen
            request = {
                "action": action,
                "symbol": symbol,
                "volume": volume,
                "type": order_type_mt5,
                "price": price,
                "sl": sl,
                "tp": tp,
                "comment": comment,
                "magic": magic,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Order senden
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"Order fehlgeschlagen: {result.retcode} - {result.comment}"
                logging.error(error_msg)
                return {'success': False, 'error': error_msg, 'retcode': result.retcode}
            
            logging.info(f"Order erfolgreich: Ticket {result.order}, {order_type} {volume} {symbol}")
            return {
                'success': True,
                'ticket': result.order,
                'volume': result.volume,
                'price': result.price,
                'comment': result.comment
            }
            
        except Exception as e:
            error_msg = f"Fehler beim Platzieren der Order: {e}"
            logging.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def close_position(self, ticket: int) -> Dict[str, Any]:
        """Position schließen"""
        if not self.connected:
            return {'success': False, 'error': 'Nicht mit MT5 verbunden'}
        
        try:
            # Position-Info abrufen
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return {'success': False, 'error': 'Position nicht gefunden'}
            
            position = positions[0]
            
            # Gegenteilige Order platzieren
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "comment": f"Close position {ticket}",
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"Position schließen fehlgeschlagen: {result.retcode}"
                logging.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            logging.info(f"Position {ticket} erfolgreich geschlossen")
            return {'success': True, 'ticket': result.order}
            
        except Exception as e:
            error_msg = f"Fehler beim Schließen der Position: {e}"
            logging.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Alle offenen Positionen abrufen"""
        if not self.connected:
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'current_price': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'comment': pos.comment,
                    'magic': pos.magic,
                    'open_time': datetime.fromtimestamp(pos.time)
                })
            
            return result
            
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Positionen: {e}")
            return []
    
    def get_history_orders(self, days: int = 30) -> List[Dict[str, Any]]:
        """Historische Orders abrufen"""
        if not self.connected:
            return []
        
        try:
            # Zeitraum definieren
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
            
            deals = mt5.history_deals_get(from_date, to_date)
            if deals is None:
                return []
            
            result = []
            for deal in deals:
                result.append({
                    'ticket': deal.ticket,
                    'order': deal.order,
                    'symbol': deal.symbol,
                    'type': 'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL',
                    'volume': deal.volume,
                    'price': deal.price,
                    'commission': deal.commission,
                    'swap': deal.swap,
                    'profit': deal.profit,
                    'comment': deal.comment,
                    'magic': deal.magic,
                    'time': datetime.fromtimestamp(deal.time)
                })
            
            return result
            
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Historie: {e}")
            return []

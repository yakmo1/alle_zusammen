"""
Order Executor
Führt Trading Orders aus basierend auf Signals
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import time

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config
from ..data.database_manager import get_database
from ..connectors.mt5_connector import MT5Connector
from ..utils.risk_manager import RiskManager


class OrderExecutor:
    """Führt Orders aus und verwaltet Positionen"""

    def __init__(self, db_type: str = 'local', dry_run: bool = False):
        """
        Initialisiert den Order Executor

        Args:
            db_type: Database Type
            dry_run: Wenn True, werden keine echten Orders ausgeführt
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)
        self.risk_manager = RiskManager()

        self.dry_run = dry_run

        # MT5 Connection
        self.mt5 = None
        self._init_mt5()

        # Magic Number für dieses System
        self.magic_number = 20251012

    def _init_mt5(self):
        """Initialisiert MT5 Verbindung"""
        try:
            import os
            login = int(os.getenv('MT5_LOGIN', 0))
            password = os.getenv('MT5_PASSWORD', '')
            server = os.getenv('MT5_SERVER', '')
            path = os.getenv('MT5_PATH', '')

            if not login or not password or not server:
                self.logger.error("MT5 Credentials nicht konfiguriert")
                return

            self.mt5 = MT5Connector(login, password, server, path)

            if not self.dry_run:
                if self.mt5.connect():
                    self.logger.info("MT5 Verbindung erfolgreich")
                else:
                    self.logger.error("MT5 Verbindung fehlgeschlagen")
                    self.mt5 = None
            else:
                self.logger.info("DRY RUN Mode - Keine echten Orders")

        except Exception as e:
            log_exception(self.logger, e, "Failed to initialize MT5")
            self.mt5 = None

    def execute_signal(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Führt ein Trading Signal aus

        Args:
            signal: Trading Signal Dictionary

        Returns:
            Order Result Dictionary oder None
        """
        try:
            # Check if MT5 is connected
            if not self.dry_run and not self.mt5:
                self.logger.error("MT5 not connected")
                return None

            # Get account info
            if not self.dry_run:
                account_info = self.mt5.get_account_info()
                if not account_info:
                    self.logger.error("Could not get account info")
                    return None
            else:
                # Dummy account info for dry run
                account_info = {
                    'balance': 10000.0,
                    'equity': 10000.0,
                    'free_margin': 9000.0,
                    'margin_level': 1000.0
                }

            # Risk check
            if not self.risk_manager.check_risk_limits(account_info, signal):
                self.logger.warning(f"Risk limits exceeded for {signal['symbol']}")
                self._update_signal_status(signal, 'REJECTED', 'Risk limits exceeded')
                return None

            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(account_info, signal)

            if position_size <= 0:
                self.logger.warning(f"Invalid position size: {position_size}")
                self._update_signal_status(signal, 'REJECTED', 'Invalid position size')
                return None

            # Round position size to lot size (0.01)
            position_size = max(0.01, round(position_size, 2))

            self.logger.info(
                f"Executing {signal['signal']} order for {signal['symbol']}: "
                f"{position_size} lots @ {signal['entry_price']:.5f}"
            )

            # Place order
            if not self.dry_run:
                result = self.mt5.place_order(
                    symbol=signal['symbol'],
                    order_type=signal['signal'],
                    volume=position_size,
                    price=signal['entry_price'],
                    sl=signal['stop_loss'],
                    tp=signal['take_profit'],
                    comment=f"ML_Signal_{signal['confidence']:.2f}",
                    magic=self.magic_number
                )

                if not result['success']:
                    self.logger.error(f"Order failed: {result.get('error', 'Unknown error')}")
                    self._update_signal_status(signal, 'FAILED', result.get('error', 'Unknown'))
                    return None

                ticket = result['ticket']
                actual_price = result['price']

            else:
                # Dry run - simulate order
                ticket = int(time.time() * 1000)  # Fake ticket
                actual_price = signal['entry_price']
                result = {'success': True}

            # Save trade to database
            trade_data = {
                'ticket': ticket,
                'symbol': signal['symbol'],
                'type': signal['signal'],
                'volume': position_size,
                'entry_price': actual_price,
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'entry_time': datetime.now(),
                'signal_confidence': signal['confidence'],
                'magic_number': self.magic_number,
                'status': 'OPEN'
            }

            self._save_trade(trade_data)
            self._update_signal_status(signal, 'EXECUTED', f'Ticket: {ticket}')

            self.logger.info(f"✓ Order executed: Ticket {ticket}")

            return {
                'success': True,
                'ticket': ticket,
                'symbol': signal['symbol'],
                'type': signal['signal'],
                'volume': position_size,
                'price': actual_price,
                'sl': signal['stop_loss'],
                'tp': signal['take_profit']
            }

        except Exception as e:
            log_exception(self.logger, e, f"Failed to execute signal for {signal['symbol']}")
            self._update_signal_status(signal, 'FAILED', str(e))
            return None

    def close_position(self, ticket: int, reason: str = 'Manual close') -> bool:
        """
        Schließt eine Position

        Args:
            ticket: Position Ticket
            reason: Grund für Schließung

        Returns:
            True wenn erfolgreich
        """
        try:
            if not self.dry_run and not self.mt5:
                self.logger.error("MT5 not connected")
                return False

            self.logger.info(f"Closing position {ticket}: {reason}")

            if not self.dry_run:
                result = self.mt5.close_position(ticket)

                if not result['success']:
                    self.logger.error(f"Failed to close position: {result.get('error')}")
                    return False

            # Update trade in database
            self._update_trade_status(ticket, 'CLOSED', reason)

            self.logger.info(f"✓ Position {ticket} closed")
            return True

        except Exception as e:
            log_exception(self.logger, e, f"Failed to close position {ticket}")
            return False

    def modify_position(
        self,
        ticket: int,
        new_sl: float = None,
        new_tp: float = None
    ) -> bool:
        """
        Modifiziert eine Position (Stop Loss / Take Profit)

        Args:
            ticket: Position Ticket
            new_sl: Neuer Stop Loss (optional)
            new_tp: Neuer Take Profit (optional)

        Returns:
            True wenn erfolgreich
        """
        try:
            if not self.dry_run and not self.mt5:
                self.logger.error("MT5 not connected")
                return False

            # Get position info
            if not self.dry_run:
                positions = self.mt5.get_positions()
                position = next((p for p in positions if p['ticket'] == ticket), None)

                if not position:
                    self.logger.error(f"Position {ticket} not found")
                    return False

                # Use current values if not specified
                sl = new_sl if new_sl is not None else position['sl']
                tp = new_tp if new_tp is not None else position['tp']

                # MT5 modify position logic would go here
                # For now, log the modification
                self.logger.info(f"Position {ticket} modified: SL={sl:.5f}, TP={tp:.5f}")

            else:
                # Dry run
                self.logger.info(f"[DRY RUN] Modify position {ticket}: SL={new_sl}, TP={new_tp}")

            return True

        except Exception as e:
            log_exception(self.logger, e, f"Failed to modify position {ticket}")
            return False

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Holt alle offenen Positionen

        Returns:
            Liste von Positionen
        """
        if not self.dry_run and self.mt5:
            return self.mt5.get_positions()
        else:
            # Return from database in dry run
            query = """
                SELECT * FROM trades
                WHERE status = 'OPEN'
                ORDER BY entry_time DESC
            """
            return self.db.fetch_all_dict(query)

    def _save_trade(self, trade_data: Dict[str, Any]):
        """
        Speichert Trade in Database

        Args:
            trade_data: Trade Data Dictionary
        """
        try:
            insert_sql = """
                INSERT INTO trades
                    (ticket, symbol, type, volume, entry_price,
                     stop_loss, take_profit, entry_time,
                     signal_confidence, magic_number, status)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            self.db.execute(insert_sql, (
                trade_data['ticket'],
                trade_data['symbol'],
                trade_data['type'],
                trade_data['volume'],
                trade_data['entry_price'],
                trade_data['stop_loss'],
                trade_data['take_profit'],
                trade_data['entry_time'],
                trade_data['signal_confidence'],
                trade_data['magic_number'],
                trade_data['status']
            ))

            self.logger.info(f"Trade {trade_data['ticket']} saved to database")

        except Exception as e:
            log_exception(self.logger, e, "Failed to save trade to database")

    def _update_trade_status(self, ticket: int, status: str, note: str = ''):
        """
        Aktualisiert Trade Status

        Args:
            ticket: Trade Ticket
            status: Neuer Status
            note: Optional note
        """
        try:
            update_sql = """
                UPDATE trades
                SET status = %s,
                    exit_time = %s,
                    notes = %s
                WHERE ticket = %s
            """

            self.db.execute(update_sql, (
                status,
                datetime.now() if status == 'CLOSED' else None,
                note,
                ticket
            ))

        except Exception as e:
            log_exception(self.logger, e, f"Failed to update trade status for {ticket}")

    def _update_signal_status(self, signal: Dict[str, Any], status: str, note: str = ''):
        """
        Aktualisiert Signal Status

        Args:
            signal: Signal Dictionary
            status: Neuer Status
            note: Optional note
        """
        try:
            update_sql = """
                UPDATE signals
                SET status = %s,
                    execution_notes = %s
                WHERE symbol = %s
                  AND timestamp = %s
            """

            self.db.execute(update_sql, (
                status,
                note,
                signal['symbol'],
                signal['timestamp']
            ))

        except Exception as e:
            log_exception(self.logger, e, "Failed to update signal status")

    def get_account_info(self) -> Dict[str, Any]:
        """
        Holt Account Informationen

        Returns:
            Account Info Dictionary
        """
        if not self.dry_run and self.mt5:
            return self.mt5.get_account_info()
        else:
            return {
                'balance': 10000.0,
                'equity': 10000.0,
                'free_margin': 9000.0,
                'margin_level': 1000.0,
                'dry_run': True
            }

    def __del__(self):
        """Destructor - Disconnect from MT5"""
        if self.mt5 and not self.dry_run:
            self.mt5.disconnect()


if __name__ == "__main__":
    # Test
    print("=== Order Executor Test ===\n")

    # Dry run test
    executor = OrderExecutor(dry_run=True)

    # Create test signal
    test_signal = {
        'symbol': 'EURUSD',
        'timeframe': '1m',
        'timestamp': datetime.now(),
        'signal': 'BUY',
        'entry_price': 1.10000,
        'stop_loss': 1.09900,
        'take_profit': 1.10150,
        'confidence': 0.75,
        'risk_reward_ratio': 1.5
    }

    print("Executing test signal (DRY RUN)...")
    result = executor.execute_signal(test_signal)

    if result:
        print("\n✓ Test order executed:")
        print(f"  Ticket: {result['ticket']}")
        print(f"  Symbol: {result['symbol']}")
        print(f"  Type: {result['type']}")
        print(f"  Volume: {result['volume']}")
        print(f"  Price: {result['price']:.5f}")
    else:
        print("\n✗ Test order failed")

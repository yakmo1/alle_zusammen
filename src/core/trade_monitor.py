"""
Trade Monitor
Überwacht offene Trades und managed Stop Loss / Take Profit
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import time
from collections import defaultdict

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config
from ..data.database_manager import get_database
from .order_executor import OrderExecutor


class TradeMonitor:
    """Überwacht und verwaltet offene Trades"""

    def __init__(self, executor: OrderExecutor, db_type: str = 'local'):
        """
        Initialisiert den Trade Monitor

        Args:
            executor: Order Executor Instanz
            db_type: Database Type
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)
        self.executor = executor

        # Configuration
        self.check_interval = 5  # Sekunden
        self.trailing_stop_enabled = True
        self.trailing_stop_distance_pips = 20  # Pips
        self.breakeven_trigger_pips = 15  # Move SL to BE after +15 pips
        self.max_position_duration_hours = 24  # Close after 24h

        # State
        self.is_running = False
        self.monitor_thread = None

        # Statistics
        self.stats = {
            'trades_monitored': 0,
            'stop_losses_adjusted': 0,
            'positions_closed': 0,
            'breakeven_adjustments': 0,
            'start_time': None
        }

        # Trade tracking
        self.tracked_trades = {}  # ticket -> trade_info

    def _monitor_loop(self):
        """Monitor Loop (läuft in eigenem Thread)"""
        self.logger.info("Trade monitor started")

        while self.is_running:
            try:
                # Get open positions
                positions = self.executor.get_open_positions()

                if positions:
                    self.logger.info(f"Monitoring {len(positions)} open positions")
                    self.stats['trades_monitored'] = len(positions)

                    for position in positions:
                        self._monitor_position(position)

                # Check for stale trades
                self._check_stale_trades()

                # Sleep
                time.sleep(self.check_interval)

            except Exception as e:
                log_exception(self.logger, e, "Error in trade monitor loop")
                time.sleep(1)

        self.logger.info("Trade monitor stopped")

    def _monitor_position(self, position: Dict[str, Any]):
        """
        Überwacht eine einzelne Position

        Args:
            position: Position Dictionary
        """
        try:
            ticket = position['ticket']
            symbol = position['symbol']
            position_type = position['type']
            entry_price = float(position['open_price'])
            current_price = float(position.get('current_price', entry_price))
            sl = float(position.get('sl', 0))
            tp = float(position.get('tp', 0))
            profit = float(position.get('profit', 0))

            # Track trade info
            if ticket not in self.tracked_trades:
                self.tracked_trades[ticket] = {
                    'entry_time': position.get('open_time', datetime.now()),
                    'highest_profit': profit,
                    'lowest_profit': profit,
                    'sl_adjusted': False
                }

            trade_info = self.tracked_trades[ticket]

            # Update profit tracking
            trade_info['highest_profit'] = max(trade_info['highest_profit'], profit)
            trade_info['lowest_profit'] = min(trade_info['lowest_profit'], profit)

            # Calculate profit in pips
            if position_type == 'BUY':
                profit_pips = (current_price - entry_price) * 10000
            else:  # SELL
                profit_pips = (entry_price - current_price) * 10000

            self.logger.debug(
                f"Position {ticket}: {symbol} {position_type} @ {current_price:.5f}, "
                f"Profit: {profit:.2f} ({profit_pips:.1f} pips)"
            )

            # Check for breakeven adjustment
            if not trade_info['sl_adjusted'] and profit_pips >= self.breakeven_trigger_pips:
                self._move_to_breakeven(position, entry_price)
                trade_info['sl_adjusted'] = True
                self.stats['breakeven_adjustments'] += 1

            # Check for trailing stop
            if self.trailing_stop_enabled and profit_pips > self.trailing_stop_distance_pips:
                self._apply_trailing_stop(position, current_price, profit_pips)

            # Check for time-based exit
            position_age = datetime.now() - trade_info['entry_time']
            if position_age > timedelta(hours=self.max_position_duration_hours):
                self.logger.info(f"Closing position {ticket}: exceeded max duration")
                self.executor.close_position(ticket, f"Max duration exceeded ({self.max_position_duration_hours}h)")
                self.stats['positions_closed'] += 1
                del self.tracked_trades[ticket]

        except Exception as e:
            log_exception(self.logger, e, f"Error monitoring position {position.get('ticket')}")

    def _move_to_breakeven(self, position: Dict[str, Any], entry_price: float):
        """
        Bewegt Stop Loss auf Breakeven

        Args:
            position: Position Dictionary
            entry_price: Entry Price
        """
        try:
            ticket = position['ticket']
            symbol = position['symbol']
            current_sl = float(position.get('sl', 0))

            # Add small buffer (1 pip)
            pip = 0.0001
            if position['type'] == 'BUY':
                new_sl = entry_price + pip
            else:  # SELL
                new_sl = entry_price - pip

            # Only adjust if new SL is better
            if position['type'] == 'BUY' and new_sl > current_sl:
                self.executor.modify_position(ticket, new_sl=new_sl)
                self.logger.info(f"✓ Moved {symbol} to breakeven: SL={new_sl:.5f}")
            elif position['type'] == 'SELL' and new_sl < current_sl:
                self.executor.modify_position(ticket, new_sl=new_sl)
                self.logger.info(f"✓ Moved {symbol} to breakeven: SL={new_sl:.5f}")

        except Exception as e:
            log_exception(self.logger, e, f"Error moving position to breakeven")

    def _apply_trailing_stop(
        self,
        position: Dict[str, Any],
        current_price: float,
        profit_pips: float
    ):
        """
        Wendet Trailing Stop an

        Args:
            position: Position Dictionary
            current_price: Aktueller Preis
            profit_pips: Profit in Pips
        """
        try:
            ticket = position['ticket']
            symbol = position['symbol']
            position_type = position['type']
            current_sl = float(position.get('sl', 0))

            # Calculate trailing stop level
            pip = 0.0001
            trailing_distance = self.trailing_stop_distance_pips * pip

            if position_type == 'BUY':
                new_sl = current_price - trailing_distance
                # Only move SL up, never down
                if new_sl > current_sl:
                    self.executor.modify_position(ticket, new_sl=new_sl)
                    self.logger.info(
                        f"✓ Trailing stop adjusted for {symbol}: "
                        f"SL={new_sl:.5f} ({self.trailing_stop_distance_pips} pips)"
                    )
                    self.stats['stop_losses_adjusted'] += 1
            else:  # SELL
                new_sl = current_price + trailing_distance
                # Only move SL down, never up
                if new_sl < current_sl or current_sl == 0:
                    self.executor.modify_position(ticket, new_sl=new_sl)
                    self.logger.info(
                        f"✓ Trailing stop adjusted for {symbol}: "
                        f"SL={new_sl:.5f} ({self.trailing_stop_distance_pips} pips)"
                    )
                    self.stats['stop_losses_adjusted'] += 1

        except Exception as e:
            log_exception(self.logger, e, f"Error applying trailing stop")

    def _check_stale_trades(self):
        """Prüft auf veraltete Trades im Tracking"""
        try:
            # Get current open positions
            positions = self.executor.get_open_positions()
            open_tickets = {p['ticket'] for p in positions}

            # Remove tracked trades that are no longer open
            stale_tickets = [t for t in self.tracked_trades.keys() if t not in open_tickets]

            for ticket in stale_tickets:
                self.logger.info(f"Removing stale trade from tracking: {ticket}")
                del self.tracked_trades[ticket]

        except Exception as e:
            log_exception(self.logger, e, "Error checking stale trades")

    def start(self):
        """Startet den Trade Monitor"""
        if self.is_running:
            self.logger.warning("Trade monitor already running")
            return

        self.logger.info("Starting trade monitor...")

        self.is_running = True
        self.stats['start_time'] = datetime.now()

        # Start thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        self.logger.info(f"✓ Trade monitor started (check interval: {self.check_interval}s)")

    def stop(self):
        """Stoppt den Trade Monitor"""
        if not self.is_running:
            return

        self.logger.info("Stopping trade monitor...")

        self.is_running = False

        # Wait for thread
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)

        # Log statistics
        self._log_statistics()

        self.logger.info("✓ Trade monitor stopped")

    def _log_statistics(self):
        """Loggt Statistiken"""
        if self.stats['start_time']:
            runtime = (datetime.now() - self.stats['start_time']).total_seconds()

            self.logger.info("=== Trade Monitor Statistics ===")
            self.logger.info(f"Runtime: {runtime:.0f}s")
            self.logger.info(f"Trades Monitored: {self.stats['trades_monitored']}")
            self.logger.info(f"Stop Losses Adjusted: {self.stats['stop_losses_adjusted']}")
            self.logger.info(f"Breakeven Adjustments: {self.stats['breakeven_adjustments']}")
            self.logger.info(f"Positions Closed: {self.stats['positions_closed']}")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Holt Monitoring Status

        Returns:
            Status Dictionary
        """
        return {
            'is_running': self.is_running,
            'tracked_trades': len(self.tracked_trades),
            'stats': self.stats,
            'config': {
                'check_interval': self.check_interval,
                'trailing_stop_enabled': self.trailing_stop_enabled,
                'trailing_stop_distance_pips': self.trailing_stop_distance_pips,
                'breakeven_trigger_pips': self.breakeven_trigger_pips,
                'max_position_duration_hours': self.max_position_duration_hours
            }
        }

    def __enter__(self):
        """Context Manager Enter"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Exit"""
        self.stop()


if __name__ == "__main__":
    # Test
    print("=== Trade Monitor Test ===\n")

    from .order_executor import OrderExecutor

    # Create executor and monitor
    executor = OrderExecutor(dry_run=True)
    monitor = TradeMonitor(executor)

    print("Starting trade monitor for 30 seconds...")
    monitor.start()

    # Simulate for 30 seconds
    time.sleep(30)

    monitor.stop()

    # Print status
    status = monitor.get_monitoring_status()
    print("\nMonitoring Status:")
    print(f"  Tracked Trades: {status['tracked_trades']}")
    print(f"  Stats: {status['stats']}")

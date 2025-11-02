"""
Tick Collector
Sammelt Tick-Daten von MT5 und speichert sie in PostgreSQL
"""

import MetaTrader5 as mt5
import time
from datetime import datetime, date
from typing import List, Dict, Any
import threading
from queue import Queue

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config
from .database_manager import get_database


class TickCollector:
    """Sammelt Tick-Daten von MT5"""

    def __init__(self, symbols: List[str] = None, db_type: str = 'local'):
        """
        Initialisiert den Tick Collector

        Args:
            symbols: Liste der zu überwachenden Symbols (None = aus Config)
            db_type: Database Type ('local' oder 'remote')
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)

        # Symbols
        self.symbols = symbols or self.config.get_symbols()

        # Tick Queue für Batch Insert
        self.tick_queue = Queue(maxsize=1000)
        self.batch_size = 100
        self.batch_interval = 5  # Sekunden

        # State
        self.is_running = False
        self.mt5_connected = False
        self.current_date = None
        self.current_table = None

        # Threads
        self.collector_thread = None
        self.writer_thread = None

        # Statistics
        self.stats = {
            'ticks_collected': 0,
            'ticks_written': 0,
            'errors': 0,
            'start_time': None
        }

    def _connect_mt5(self) -> bool:
        """
        Verbindet mit MT5

        Returns:
            True wenn Verbindung erfolgreich
        """
        try:
            mt5_config = self.config.get_mt5_config()

            # Initialize
            if not mt5.initialize(path=mt5_config.get('path')):
                error = mt5.last_error()
                self.logger.error(f"MT5 initialization failed: {error}")
                return False

            # Login
            if not mt5.login(
                login=mt5_config['login'],
                password=mt5_config['password'],
                server=mt5_config['server']
            ):
                error = mt5.last_error()
                self.logger.error(f"MT5 login failed: {error}")
                mt5.shutdown()
                return False

            self.logger.info("✓ MT5 connected")
            self.mt5_connected = True

            # Enable Symbols
            for symbol in self.symbols:
                if not mt5.symbol_select(symbol, True):
                    self.logger.warning(f"Could not enable symbol: {symbol}")

            return True

        except Exception as e:
            log_exception(self.logger, e, "MT5 connection failed")
            return False

    def _disconnect_mt5(self):
        """Trennt MT5 Verbindung"""
        if self.mt5_connected:
            mt5.shutdown()
            self.mt5_connected = False
            self.logger.info("MT5 disconnected")

    def _get_today_table_name(self) -> str:
        """
        Holt Table Name für heute

        Returns:
            Table Name (z.B. ticks_20251012)
        """
        today = date.today()
        return f"ticks_{today.strftime('%Y%m%d')}"

    def _ensure_daily_table(self):
        """Stellt sicher dass Tabelle für heute existiert"""
        today = date.today()

        # Check if new day
        if self.current_date != today:
            self.current_date = today
            self.current_table = self._get_today_table_name()

            # Create table if not exists
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.current_table} (
                    id BIGSERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    bid DECIMAL(10, 5) NOT NULL,
                    ask DECIMAL(10, 5) NOT NULL,
                    last DECIMAL(10, 5),
                    volume BIGINT,
                    time_msc BIGINT
                );

                CREATE INDEX IF NOT EXISTS idx_{self.current_table}_timestamp
                    ON {self.current_table} (timestamp DESC);

                CREATE INDEX IF NOT EXISTS idx_{self.current_table}_symbol
                    ON {self.current_table} (symbol, timestamp DESC);
            """

            try:
                self.db.execute(create_sql)
                self.logger.info(f"✓ Daily table ready: {self.current_table}")
            except Exception as e:
                log_exception(self.logger, e, f"Failed to create daily table: {self.current_table}")

    def _collect_ticks(self):
        """Sammelt Ticks von MT5 (läuft in eigenem Thread)"""
        self.logger.info("Tick collection started")

        while self.is_running:
            try:
                # Ensure MT5 connected
                if not self.mt5_connected:
                    self.logger.warning("MT5 not connected, reconnecting...")
                    if not self._connect_mt5():
                        time.sleep(10)
                        continue

                # Ensure daily table exists
                self._ensure_daily_table()

                # Collect ticks for all symbols
                for symbol in self.symbols:
                    tick = mt5.symbol_info_tick(symbol)

                    if tick is None:
                        continue

                    # Tick Data
                    tick_data = {
                        'symbol': symbol,
                        'timestamp': datetime.fromtimestamp(tick.time),
                        'bid': tick.bid,
                        'ask': tick.ask,
                        'last': tick.last,
                        'volume': tick.volume,
                        'time_msc': tick.time_msc
                    }

                    # Add to queue
                    try:
                        self.tick_queue.put(tick_data, block=False)
                        self.stats['ticks_collected'] += 1
                    except:
                        # Queue full
                        pass

                # Sleep kurz (ca. 100ms = 10 ticks/sec pro Symbol)
                time.sleep(0.1)

            except Exception as e:
                log_exception(self.logger, e, "Error in tick collection")
                self.stats['errors'] += 1
                time.sleep(1)

        self.logger.info("Tick collection stopped")

    def _write_ticks(self):
        """Schreibt Ticks in Database (läuft in eigenem Thread)"""
        self.logger.info("Tick writer started")

        batch = []
        last_write = time.time()

        while self.is_running or not self.tick_queue.empty():
            try:
                # Get tick from queue (with timeout)
                try:
                    tick_data = self.tick_queue.get(timeout=1)
                    batch.append(tick_data)
                except:
                    pass  # Timeout, check if should write

                # Write batch if:
                # 1. Batch size reached
                # 2. Batch interval passed
                # 3. System stopping
                current_time = time.time()
                should_write = (
                    len(batch) >= self.batch_size or
                    (len(batch) > 0 and current_time - last_write >= self.batch_interval) or
                    not self.is_running
                )

                if should_write and len(batch) > 0:
                    self._write_batch(batch)
                    self.stats['ticks_written'] += len(batch)
                    batch = []
                    last_write = current_time

            except Exception as e:
                log_exception(self.logger, e, "Error in tick writer")
                self.stats['errors'] += 1
                time.sleep(1)

        self.logger.info("Tick writer stopped")

    def _write_batch(self, batch: List[Dict[str, Any]]):
        """
        Schreibt Batch von Ticks in Database

        Args:
            batch: Liste von Tick-Daten
        """
        if not batch:
            return

        # Ensure table exists
        self._ensure_daily_table()

        # Prepare SQL
        insert_sql = f"""
            INSERT INTO {self.current_table}
                (symbol, timestamp, bid, ask, last, volume, time_msc)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """

        # Prepare values
        values = [
            (
                tick['symbol'],
                tick['timestamp'],
                tick['bid'],
                tick['ask'],
                tick['last'],
                tick['volume'],
                tick['time_msc']
            )
            for tick in batch
        ]

        # Execute
        try:
            self.db.execute_many(insert_sql, values)
        except Exception as e:
            log_exception(self.logger, e, f"Failed to write batch of {len(batch)} ticks")

    def start(self):
        """Startet den Tick Collector"""
        if self.is_running:
            self.logger.warning("Tick collector already running")
            return

        self.logger.info("Starting tick collector...")

        # Connect to MT5
        if not self._connect_mt5():
            self.logger.error("Failed to connect to MT5")
            return

        # Start collection
        self.is_running = True
        self.stats['start_time'] = datetime.now()

        # Start threads
        self.collector_thread = threading.Thread(target=self._collect_ticks, daemon=True)
        self.writer_thread = threading.Thread(target=self._write_ticks, daemon=True)

        self.collector_thread.start()
        self.writer_thread.start()

        self.logger.info(f"✓ Tick collector started for symbols: {', '.join(self.symbols)}")

    def stop(self):
        """Stoppt den Tick Collector"""
        if not self.is_running:
            return

        self.logger.info("Stopping tick collector...")

        # Stop collection
        self.is_running = False

        # Wait for threads
        if self.collector_thread:
            self.collector_thread.join(timeout=10)
        if self.writer_thread:
            self.writer_thread.join(timeout=10)

        # Disconnect MT5
        self._disconnect_mt5()

        # Log statistics
        self._log_statistics()

        self.logger.info("✓ Tick collector stopped")

    def _log_statistics(self):
        """Loggt Statistiken"""
        if self.stats['start_time']:
            runtime = (datetime.now() - self.stats['start_time']).total_seconds()
            rate = self.stats['ticks_collected'] / runtime if runtime > 0 else 0

            self.logger.info("=== Tick Collector Statistics ===")
            self.logger.info(f"Runtime: {runtime:.0f}s")
            self.logger.info(f"Ticks Collected: {self.stats['ticks_collected']}")
            self.logger.info(f"Ticks Written: {self.stats['ticks_written']}")
            self.logger.info(f"Rate: {rate:.1f} ticks/sec")
            self.logger.info(f"Errors: {self.stats['errors']}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Holt aktuelle Statistiken

        Returns:
            Statistics Dictionary
        """
        stats = self.stats.copy()
        if stats['start_time']:
            stats['runtime'] = (datetime.now() - stats['start_time']).total_seconds()
        return stats

    def __enter__(self):
        """Context Manager Enter"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Exit"""
        self.stop()


if __name__ == "__main__":
    # Test
    print("=== Tick Collector Test ===\n")

    try:
        collector = TickCollector(symbols=['EURUSD'])
        collector.start()

        # Run for 30 seconds
        print("Collecting ticks for 30 seconds...")
        time.sleep(30)

        # Stop
        collector.stop()

        # Stats
        print("\nStatistics:")
        stats = collector.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        if collector:
            collector.stop()
    except Exception as e:
        print(f"Error: {e}")

"""
Bar Builder
Aggregiert Tick-Daten zu OHLC Bars für verschiedene Timeframes
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
import threading
from collections import defaultdict

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config
from .database_manager import get_database


class BarBuilder:
    """Baut OHLC Bars aus Tick-Daten"""

    def __init__(self, symbols: List[str] = None, timeframes: List[str] = None, db_type: str = 'local'):
        """
        Initialisiert den Bar Builder

        Args:
            symbols: Liste der Symbols (None = aus Config)
            timeframes: Liste der Timeframes (None = aus Config)
            db_type: Database Type
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)

        # Configuration
        self.symbols = symbols or self.config.get_symbols()
        self.timeframes = timeframes or self.config.get_bar_types()

        # Timeframe Mappings (in Sekunden)
        self.timeframe_seconds = {
            '5s': 5,
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }

        # Current Bars (per Symbol + Timeframe)
        self.current_bars = defaultdict(lambda: defaultdict(lambda: None))

        # State
        self.is_running = False
        self.builder_thread = None

        # Statistics
        self.stats = {
            'bars_built': defaultdict(int),
            'ticks_processed': 0,
            'start_time': None
        }

    def _get_bar_table(self, timeframe: str) -> str:
        """
        Holt Tabellen-Name für Timeframe

        Args:
            timeframe: Timeframe (z.B. '1m', '5m')

        Returns:
            Table Name
        """
        return f"bars_{timeframe}"

    def _round_timestamp_to_timeframe(self, timestamp: datetime, timeframe: str) -> datetime:
        """
        Rundet Timestamp auf Timeframe

        Args:
            timestamp: Original Timestamp
            timeframe: Timeframe

        Returns:
            Gerundeter Timestamp
        """
        seconds = self.timeframe_seconds.get(timeframe, 60)

        # Sekunden seit Epoch
        epoch = int(timestamp.timestamp())

        # Runden auf Timeframe
        rounded_epoch = (epoch // seconds) * seconds

        return datetime.fromtimestamp(rounded_epoch)

    def _fetch_latest_ticks(self, symbol: str, since: datetime = None) -> List[Dict[str, Any]]:
        """
        Holt neueste Ticks für Symbol

        Args:
            symbol: Trading Symbol
            since: Ab diesem Timestamp (None = letzte Minute)

        Returns:
            Liste von Ticks
        """
        if since is None:
            since = datetime.now() - timedelta(minutes=1)

        # Get today's table
        from datetime import date
        today = date.today()
        table_name = f"ticks_{today.strftime('%Y%m%d')}"

        # Check if table exists
        if not self.db.table_exists(table_name):
            return []

        # Fetch ticks
        query = f"""
            SELECT symbol, timestamp, bid, ask, last, volume
            FROM {table_name}
            WHERE symbol = %s
              AND timestamp >= %s
            ORDER BY timestamp ASC
        """

        try:
            results = self.db.fetch_all_dict(query, (symbol, since))
            return results
        except Exception as e:
            log_exception(self.logger, e, f"Failed to fetch ticks for {symbol}")
            return []

    def _process_tick(self, tick: Dict[str, Any], timeframe: str):
        """
        Verarbeitet einen Tick für ein Timeframe

        Args:
            tick: Tick Data
            timeframe: Timeframe
        """
        symbol = tick['symbol']
        timestamp = tick['timestamp']
        price = float(tick['last'] or tick['bid'])  # Last oder Bid

        # Round timestamp to timeframe
        bar_timestamp = self._round_timestamp_to_timeframe(timestamp, timeframe)

        # Get current bar
        current_bar = self.current_bars[symbol][timeframe]

        # Check if new bar needed
        if current_bar is None or current_bar['timestamp'] != bar_timestamp:
            # Save previous bar
            if current_bar is not None:
                self._save_bar(current_bar, timeframe)

            # Create new bar
            current_bar = {
                'symbol': symbol,
                'timestamp': bar_timestamp,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': tick.get('volume', 0),
                'tick_count': 1
            }
            self.current_bars[symbol][timeframe] = current_bar
        else:
            # Update existing bar
            current_bar['high'] = max(current_bar['high'], price)
            current_bar['low'] = min(current_bar['low'], price)
            current_bar['close'] = price
            current_bar['volume'] += tick.get('volume', 0)
            current_bar['tick_count'] += 1

    def _save_bar(self, bar: Dict[str, Any], timeframe: str):
        """
        Speichert Bar in Database

        Args:
            bar: Bar Data
            timeframe: Timeframe
        """
        table_name = self._get_bar_table(timeframe)

        insert_sql = f"""
            INSERT INTO {table_name}
                (symbol, timestamp, open, high, low, close, volume, tick_count)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timestamp)
            DO UPDATE SET
                high = GREATEST({table_name}.high, EXCLUDED.high),
                low = LEAST({table_name}.low, EXCLUDED.low),
                close = EXCLUDED.close,
                volume = {table_name}.volume + EXCLUDED.volume,
                tick_count = {table_name}.tick_count + EXCLUDED.tick_count
        """

        values = (
            bar['symbol'],
            bar['timestamp'],
            bar['open'],
            bar['high'],
            bar['low'],
            bar['close'],
            bar['volume'],
            bar['tick_count']
        )

        try:
            self.db.execute(insert_sql, values)
            self.stats['bars_built'][timeframe] += 1
        except Exception as e:
            log_exception(self.logger, e, f"Failed to save bar for {timeframe}")

    def _build_bars(self):
        """Baut Bars (läuft in eigenem Thread)"""
        self.logger.info("Bar builder started")

        last_fetch = {}
        fetch_interval = 5  # Sekunden

        while self.is_running:
            try:
                for symbol in self.symbols:
                    # Get latest ticks
                    since = last_fetch.get(symbol, datetime.now() - timedelta(minutes=5))
                    ticks = self._fetch_latest_ticks(symbol, since)

                    # Process ticks for all timeframes
                    for tick in ticks:
                        for timeframe in self.timeframes:
                            self._process_tick(tick, timeframe)
                        self.stats['ticks_processed'] += 1

                    # Update last fetch time
                    if ticks:
                        last_fetch[symbol] = ticks[-1]['timestamp']

                # Sleep
                time.sleep(fetch_interval)

            except Exception as e:
                log_exception(self.logger, e, "Error in bar builder")
                time.sleep(1)

        # Save remaining bars
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                current_bar = self.current_bars[symbol][timeframe]
                if current_bar is not None:
                    self._save_bar(current_bar, timeframe)

        self.logger.info("Bar builder stopped")

    def start(self):
        """Startet den Bar Builder"""
        if self.is_running:
            self.logger.warning("Bar builder already running")
            return

        self.logger.info("Starting bar builder...")

        self.is_running = True
        self.stats['start_time'] = datetime.now()

        # Start thread
        self.builder_thread = threading.Thread(target=self._build_bars, daemon=True)
        self.builder_thread.start()

        self.logger.info(f"✓ Bar builder started for timeframes: {', '.join(self.timeframes)}")

    def stop(self):
        """Stoppt den Bar Builder"""
        if not self.is_running:
            return

        self.logger.info("Stopping bar builder...")

        self.is_running = False

        # Wait for thread
        if self.builder_thread:
            self.builder_thread.join(timeout=10)

        # Log statistics
        self._log_statistics()

        self.logger.info("✓ Bar builder stopped")

    def _log_statistics(self):
        """Loggt Statistiken"""
        if self.stats['start_time']:
            runtime = (datetime.now() - self.stats['start_time']).total_seconds()

            self.logger.info("=== Bar Builder Statistics ===")
            self.logger.info(f"Runtime: {runtime:.0f}s")
            self.logger.info(f"Ticks Processed: {self.stats['ticks_processed']}")
            self.logger.info("Bars Built:")
            for timeframe, count in self.stats['bars_built'].items():
                self.logger.info(f"  {timeframe}: {count}")

    def get_latest_bar(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """
        Holt neuesten Bar

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe

        Returns:
            Bar Data oder None
        """
        table_name = self._get_bar_table(timeframe)

        query = f"""
            SELECT symbol, timestamp, open, high, low, close, volume, tick_count
            FROM {table_name}
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """

        return self.db.fetch_dict(query, (symbol,))

    def get_bars(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Holt historische Bars

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            limit: Anzahl Bars

        Returns:
            Liste von Bars
        """
        table_name = self._get_bar_table(timeframe)

        query = f"""
            SELECT symbol, timestamp, open, high, low, close, volume, tick_count
            FROM {table_name}
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """

        results = self.db.fetch_all_dict(query, (symbol, limit))
        return list(reversed(results))  # Älteste zuerst

    def __enter__(self):
        """Context Manager Enter"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Exit"""
        self.stop()


if __name__ == "__main__":
    # Test
    print("=== Bar Builder Test ===\n")

    try:
        builder = BarBuilder(symbols=['EURUSD'], timeframes=['1m', '5m'])
        builder.start()

        # Run for 60 seconds
        print("Building bars for 60 seconds...")
        time.sleep(60)

        # Stop
        builder.stop()

        # Get latest bars
        print("\nLatest Bars:")
        for tf in ['1m', '5m']:
            bar = builder.get_latest_bar('EURUSD', tf)
            if bar:
                print(f"  {tf}: {bar}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        if builder:
            builder.stop()
    except Exception as e:
        print(f"Error: {e}")

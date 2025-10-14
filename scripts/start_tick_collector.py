"""
Start Tick Collector
Sammelt real-time Tick-Daten von MT5
WICHTIG: Nutzt bereits laufende MT5-Instanz (kein Login)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import MetaTrader5 as mt5
from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.data.database_manager import get_database
import time
from datetime import datetime, date
from queue import Queue
import threading

logger = get_logger('TickCollectorService')

class SimpleTickCollector:
    """Simple Tick Collector - Uses already running MT5 instance"""

    def __init__(self):
        self.config = get_config()
        self.db = get_database('local')
        self.symbols = self.config.get_symbols()
        self.tick_queue = Queue(maxsize=1000)
        self.is_running = False
        self.current_table = None
        self.stats = {'collected': 0, 'written': 0}

    def _get_today_table(self):
        """Get today's table name"""
        return f"ticks_{date.today().strftime('%Y%m%d')}"

    def _ensure_table(self):
        """Ensure today's table exists"""
        table = self._get_today_table()
        if table != self.current_table:
            self.current_table = table
            sql = f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id BIGSERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    bid DECIMAL(10, 5) NOT NULL,
                    ask DECIMAL(10, 5) NOT NULL,
                    last DECIMAL(10, 5),
                    volume BIGINT,
                    time_msc BIGINT
                );
                CREATE INDEX IF NOT EXISTS idx_{table}_timestamp ON {table} (timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_{table}_symbol ON {table} (symbol, timestamp DESC);
            """
            try:
                self.db.execute(sql)
                logger.info(f"Table ready: {table}")
            except Exception as e:
                logger.error(f"Table creation error: {e}")

    def _collect_loop(self):
        """Collect ticks"""
        logger.info("Starting collection loop...")
        while self.is_running:
            try:
                self._ensure_table()

                for symbol in self.symbols:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        try:
                            self.tick_queue.put({
                                'symbol': symbol,
                                'timestamp': datetime.fromtimestamp(tick.time),
                                'bid': tick.bid,
                                'ask': tick.ask,
                                'last': tick.last,
                                'volume': tick.volume,
                                'time_msc': tick.time_msc
                            }, block=False)
                            self.stats['collected'] += 1
                        except:
                            pass  # Queue full, skip

                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Collection error: {e}")
                time.sleep(1)

    def _write_loop(self):
        """Write ticks to database"""
        logger.info("Starting write loop...")
        batch = []
        last_write = time.time()

        while self.is_running or not self.tick_queue.empty():
            try:
                # Get tick from queue
                try:
                    tick = self.tick_queue.get(timeout=1)
                    batch.append(tick)
                except:
                    pass

                # Write batch if full or timeout
                now = time.time()
                should_write = len(batch) >= 100 or (len(batch) > 0 and now - last_write > 5)

                if should_write:
                    self._ensure_table()
                    sql = f"""
                        INSERT INTO {self.current_table}
                        (symbol, timestamp, bid, ask, last, volume, time_msc)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """
                    values = [(t['symbol'], t['timestamp'], t['bid'], t['ask'],
                               t['last'], t['volume'], t['time_msc']) for t in batch]

                    try:
                        self.db.execute_many(sql, values)
                        self.stats['written'] += len(batch)
                        logger.info(f"Wrote {len(batch)} ticks to {self.current_table}")
                    except Exception as e:
                        logger.error(f"Write error: {e}")

                    batch = []
                    last_write = now

            except Exception as e:
                logger.error(f"Write loop error: {e}")
                time.sleep(1)

        # Write remaining batch
        if batch:
            try:
                self._ensure_table()
                sql = f"""
                    INSERT INTO {self.current_table}
                    (symbol, timestamp, bid, ask, last, volume, time_msc)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """
                values = [(t['symbol'], t['timestamp'], t['bid'], t['ask'],
                           t['last'], t['volume'], t['time_msc']) for t in batch]
                self.db.execute_many(sql, values)
                self.stats['written'] += len(batch)
                logger.info(f"Wrote final {len(batch)} ticks")
            except Exception as e:
                logger.error(f"Final write error: {e}")

    def start(self):
        """Start collecting"""
        self.is_running = True
        threading.Thread(target=self._collect_loop, daemon=True).start()
        threading.Thread(target=self._write_loop, daemon=True).start()
        logger.info(f"Started collecting: {', '.join(self.symbols)}")

    def stop(self):
        """Stop collecting"""
        self.is_running = False
        logger.info(f"Stats: Collected={self.stats['collected']}, Written={self.stats['written']}")

def main():
    """Main function"""
    logger.info("=" * 70)
    logger.info("TICK COLLECTOR SERVICE (Shared MT5 Mode)")
    logger.info("=" * 70)

    # Just initialize (don't login) - uses already running MT5
    try:
        if not mt5.initialize():
            logger.error("MT5 not available! Please start MT5 and login first.")
            return

        account_info = mt5.account_info()
        if not account_info:
            logger.error("MT5 not logged in! Please login to MT5 first.")
            mt5.shutdown()
            return

        logger.info(f"Connected to MT5 account: {account_info.login}")

        collector = SimpleTickCollector()
        collector.start()

        logger.info("Collecting ticks... Press Ctrl+C to stop")
        while True:
            time.sleep(10)
            if collector.stats['collected'] % 1000 == 0 and collector.stats['collected'] > 0:
                logger.info(f"Stats: {collector.stats}")

    except KeyboardInterrupt:
        logger.info("Stopping...")
        if 'collector' in locals():
            collector.stop()
            time.sleep(2)  # Wait for write queue to empty
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Tick Collector stopped")

if __name__ == '__main__':
    main()

"""
Bar Aggregator V2
- Reads from per-symbol tick tables (ticks_eurusd_20251014)
- Creates OHLC bars for multiple timeframes
- Writes to per-symbol bar tables (bars_eurusd)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import MetaTrader5 as mt5
from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.data.database_manager import get_database
import time
from datetime import datetime, timedelta, date
import pandas as pd

logger = get_logger('BarAggregatorV2')

class BarAggregator:
    """Aggregates ticks to OHLC bars"""

    def __init__(self):
        self.config = get_config()
        self.db = get_database('local')
        self.symbols = self.config.get_symbols()
        self.timeframes = ['1m', '5m', '15m', '1h', '4h']
        self.last_processed = {}  # symbol -> last timestamp processed

        # Create bar tables
        for symbol in self.symbols:
            self._ensure_bar_table(symbol)

    def _ensure_bar_table(self, symbol):
        """Create bar table for symbol if not exists"""
        table_name = f"bars_{symbol.lower()}"

        sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                timeframe VARCHAR(5) NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume BIGINT,
                tick_count INTEGER,

                -- Copy indicators from last tick in bar
                rsi14 DOUBLE PRECISION,
                macd_main DOUBLE PRECISION,
                bb_upper DOUBLE PRECISION,
                bb_lower DOUBLE PRECISION,
                atr14 DOUBLE PRECISION,

                UNIQUE(timestamp, timeframe)
            );

            CREATE INDEX IF NOT EXISTS idx_{table_name}_ts
            ON {table_name} (timestamp DESC, timeframe);
        """

        try:
            self.db.execute(sql)
            logger.info(f"Bar table ready: {table_name}")
        except Exception as e:
            logger.error(f"Error creating bar table for {symbol}: {e}")

    def _get_tick_table_name(self, symbol):
        """Get today's tick table name"""
        return f"ticks_{symbol.lower()}_{date.today().strftime('%Y%m%d')}"

    def _round_timestamp_to_timeframe(self, ts, timeframe):
        """Round timestamp to timeframe boundary"""
        if timeframe == '1m':
            return ts.replace(second=0, microsecond=0)
        elif timeframe == '5m':
            minute = (ts.minute // 5) * 5
            return ts.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == '15m':
            minute = (ts.minute // 15) * 15
            return ts.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == '1h':
            return ts.replace(minute=0, second=0, microsecond=0)
        elif timeframe == '4h':
            hour = (ts.hour // 4) * 4
            return ts.replace(hour=hour, minute=0, second=0, microsecond=0)
        return ts

    def _get_timeframe_seconds(self, timeframe):
        """Get seconds for timeframe"""
        if timeframe == '1m':
            return 60
        elif timeframe == '5m':
            return 300
        elif timeframe == '15m':
            return 900
        elif timeframe == '1h':
            return 3600
        elif timeframe == '4h':
            return 14400
        return 60

    def aggregate_symbol(self, symbol):
        """Aggregate ticks to bars for one symbol"""
        tick_table = self._get_tick_table_name(symbol)
        bar_table = f"bars_{symbol.lower()}"

        # Check if tick table exists
        check_sql = f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = '{tick_table}'
            )
        """

        exists = self.db.fetch_one(check_sql)
        if not exists or not exists[0]:
            logger.debug(f"Tick table {tick_table} does not exist yet")
            return

        # Get last processed timestamp for symbol
        if symbol not in self.last_processed:
            # Get last bar timestamp from DB
            last_bar_sql = f"""
                SELECT MAX(timestamp) FROM {bar_table} WHERE timeframe = '1m'
            """
            result = self.db.fetch_one(last_bar_sql)
            if result and result[0]:
                self.last_processed[symbol] = result[0]
            else:
                # Start from 1 hour ago
                self.last_processed[symbol] = datetime.now() - timedelta(hours=1)

        # Get new ticks since last processed
        fetch_sql = f"""
            SELECT
                mt5_ts as timestamp,
                bid,
                ask,
                volume,
                rsi14,
                macd_main,
                bb_upper,
                bb_lower,
                atr14
            FROM {tick_table}
            WHERE mt5_ts > %s
            ORDER BY mt5_ts ASC
            LIMIT 10000
        """

        ticks = self.db.fetch_all(fetch_sql, (self.last_processed[symbol],))

        if not ticks or len(ticks) == 0:
            return

        logger.info(f"[{symbol}] Processing {len(ticks)} new ticks")

        # Convert to DataFrame
        df = pd.DataFrame(ticks, columns=[
            'timestamp', 'bid', 'ask', 'volume',
            'rsi14', 'macd_main', 'bb_upper', 'bb_lower', 'atr14'
        ])

        # Use mid price for OHLC
        df['price'] = (df['bid'] + df['ask']) / 2

        # Aggregate for each timeframe
        for timeframe in self.timeframes:
            bars = self._aggregate_timeframe(df, timeframe)

            if len(bars) > 0:
                self._write_bars(symbol, timeframe, bars)

        # Update last processed timestamp
        self.last_processed[symbol] = df['timestamp'].max()

    def _aggregate_timeframe(self, df, timeframe):
        """Aggregate ticks to bars for specific timeframe"""
        df = df.copy()

        # Round timestamps to timeframe boundaries
        df['bar_time'] = df['timestamp'].apply(
            lambda x: self._round_timestamp_to_timeframe(x, timeframe)
        )

        # Group by bar_time and aggregate
        bars = df.groupby('bar_time').agg({
            'price': ['first', 'max', 'min', 'last'],  # OHLC
            'volume': 'sum',
            'timestamp': 'count',  # tick_count
            'rsi14': 'last',  # Last tick's indicators
            'macd_main': 'last',
            'bb_upper': 'last',
            'bb_lower': 'last',
            'atr14': 'last'
        })

        # Flatten column names
        bars.columns = [
            'open', 'high', 'low', 'close',
            'volume', 'tick_count',
            'rsi14', 'macd_main', 'bb_upper', 'bb_lower', 'atr14'
        ]

        bars = bars.reset_index()
        bars.rename(columns={'bar_time': 'timestamp'}, inplace=True)

        return bars

    def _write_bars(self, symbol, timeframe, bars_df):
        """Write bars to database"""
        bar_table = f"bars_{symbol.lower()}"

        sql = f"""
            INSERT INTO {bar_table}
            (timestamp, timeframe, open, high, low, close, volume, tick_count,
             rsi14, macd_main, bb_upper, bb_lower, atr14)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, timeframe) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                tick_count = EXCLUDED.tick_count,
                rsi14 = EXCLUDED.rsi14,
                macd_main = EXCLUDED.macd_main,
                bb_upper = EXCLUDED.bb_upper,
                bb_lower = EXCLUDED.bb_lower,
                atr14 = EXCLUDED.atr14
        """

        values = []
        for _, row in bars_df.iterrows():
            values.append((
                row['timestamp'],
                timeframe,
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                int(row['volume']) if pd.notna(row['volume']) else 0,
                int(row['tick_count']),
                float(row['rsi14']) if pd.notna(row['rsi14']) else None,
                float(row['macd_main']) if pd.notna(row['macd_main']) else None,
                float(row['bb_upper']) if pd.notna(row['bb_upper']) else None,
                float(row['bb_lower']) if pd.notna(row['bb_lower']) else None,
                float(row['atr14']) if pd.notna(row['atr14']) else None
            ))

        try:
            self.db.execute_many(sql, values)
            logger.info(f"[{symbol}] Wrote {len(values)} {timeframe} bars")
        except Exception as e:
            logger.error(f"[{symbol}] Error writing {timeframe} bars: {e}")

    def run(self):
        """Main loop"""
        logger.info(f"Starting bar aggregation for {len(self.symbols)} symbols")
        logger.info(f"Timeframes: {', '.join(self.timeframes)}")

        while True:
            try:
                for symbol in self.symbols:
                    self.aggregate_symbol(symbol)

                # Sleep 30 seconds between iterations
                time.sleep(30)

            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)


def main():
    """Main function"""
    logger.info("=" * 70)
    logger.info("BAR AGGREGATOR V2 - Per-Symbol Tables")
    logger.info("=" * 70)

    try:
        # MT5 not strictly needed but initialize for consistency
        if not mt5.initialize():
            logger.warning("MT5 not available, continuing anyway...")

        aggregator = BarAggregator()
        aggregator.run()

    except KeyboardInterrupt:
        logger.info("Stopping...")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Bar Aggregator V2 stopped")

if __name__ == '__main__':
    main()

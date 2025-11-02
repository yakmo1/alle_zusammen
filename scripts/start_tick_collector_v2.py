"""
Advanced Tick Collector V2
- Pro Symbol separate Tabellen (ticks_eurusd_20251013)
- Technical Indicators direkt beim Schreiben berechnet
- Orderbook Data (falls verfügbar)
- Kompatibel mit Remote Server Struktur
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import MetaTrader5 as mt5
from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.data.database_manager import get_database
import time
from datetime import datetime, date
from queue import Queue
import threading
from collections import deque
import numpy as np

logger = get_logger('TickCollectorV2')

class IndicatorCalculator:
    """Berechnet Technical Indicators aus Price-Daten"""

    def __init__(self, window_size=200):
        self.window_size = window_size
        self.price_buffers = {}  # symbol -> deque of prices

    def add_price(self, symbol, bid, ask):
        """Füge neuen Preis zu Buffer hinzu"""
        if symbol not in self.price_buffers:
            self.price_buffers[symbol] = {
                'bid': deque(maxlen=self.window_size),
                'ask': deque(maxlen=self.window_size),
                'mid': deque(maxlen=self.window_size)
            }

        mid = (bid + ask) / 2
        self.price_buffers[symbol]['bid'].append(bid)
        self.price_buffers[symbol]['ask'].append(ask)
        self.price_buffers[symbol]['mid'].append(mid)

    def calculate_indicators(self, symbol):
        """Berechne alle Indikatoren für Symbol"""
        if symbol not in self.price_buffers:
            return {}

        buffer = self.price_buffers[symbol]
        prices = np.array(buffer['mid'])

        if len(prices) < 50:
            return {}  # Nicht genug Daten

        indicators = {}

        try:
            # Moving Averages
            if len(prices) >= 14:
                indicators['ma14'] = float(np.mean(prices[-14:]))
                ema14 = self._ema(prices, 14)
                if ema14 is not None:
                    indicators['ema14'] = float(ema14)
                wma14 = self._wma(prices, 14)
                if wma14 is not None:
                    indicators['wma14'] = float(wma14)

            if len(prices) >= 50:
                indicators['ma50'] = float(np.mean(prices[-50:]))
                ema50 = self._ema(prices, 50)
                if ema50 is not None:
                    indicators['ema50'] = float(ema50)
                wma50 = self._wma(prices, 50)
                if wma50 is not None:
                    indicators['wma50'] = float(wma50)

            # RSI
            if len(prices) >= 14:
                rsi14 = self._rsi(prices, 14)
                if rsi14 is not None:
                    indicators['rsi14'] = float(rsi14)
            if len(prices) >= 28:
                rsi28 = self._rsi(prices, 28)
                if rsi28 is not None:
                    indicators['rsi28'] = float(rsi28)

            # MACD
            if len(prices) >= 26:
                macd, signal, hist = self._macd(prices)
                if macd is not None:
                    indicators['macd_main'] = float(macd)
                    indicators['macd_signal'] = float(signal)
                    indicators['macd_hist'] = float(hist)

            # ATR
            if len(prices) >= 14:
                high = float(max(prices[-14:]))
                low = float(min(prices[-14:]))
                indicators['atr14'] = high - low  # Simplified

            # Bollinger Bands
            if len(prices) >= 20:
                bb_upper, bb_mid, bb_lower = self._bollinger_bands(prices, 20, 2)
                if bb_upper is not None:
                    indicators['bb_upper'] = float(bb_upper)
                    indicators['bb_middle'] = float(bb_mid)
                    indicators['bb_lower'] = float(bb_lower)

            # ADX (simplified)
            if len(prices) >= 14:
                adx = self._adx_simplified(prices, 14)
                if adx is not None:
                    indicators['adx14'] = float(adx)

            # Momentum
            if len(prices) >= 14:
                indicators['momentum14'] = float(prices[-1] - prices[-14])

            # CCI (simplified)
            if len(prices) >= 14:
                cci = self._cci(prices, 14)
                if cci is not None:
                    indicators['cci14'] = float(cci)

            # Standard Deviation
            if len(prices) >= 14:
                indicators['stddev14'] = float(np.std(prices[-14:]))

        except Exception as e:
            logger.error(f"Indicator calculation error for {symbol}: {e}")

        return indicators

    def _ema(self, prices, period):
        """Exponential Moving Average"""
        if len(prices) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema

    def _wma(self, prices, period):
        """Weighted Moving Average"""
        if len(prices) < period:
            return None
        weights = np.arange(1, period + 1)
        return np.sum(prices[-period:] * weights) / np.sum(weights)

    def _rsi(self, prices, period=14):
        """Relative Strength Index"""
        if len(prices) < period + 1:
            return None

        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _macd(self, prices, fast=12, slow=26, signal=9):
        """MACD Indicator"""
        if len(prices) < slow:
            return None, None, None

        ema_fast = self._ema(prices, fast)
        ema_slow = self._ema(prices, slow)

        if ema_fast is None or ema_slow is None:
            return None, None, None

        macd_line = ema_fast - ema_slow

        # Signal line (simplified - should be EMA of MACD)
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def _bollinger_bands(self, prices, period=20, std_dev=2):
        """Bollinger Bands"""
        if len(prices) < period:
            return None, None, None

        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return upper, sma, lower

    def _adx_simplified(self, prices, period=14):
        """Simplified ADX"""
        if len(prices) < period:
            return None

        # Sehr vereinfacht: Volatilität als Proxy
        return np.std(prices[-period:]) / np.mean(prices[-period:]) * 100

    def _cci(self, prices, period=14):
        """Commodity Channel Index (simplified)"""
        if len(prices) < period:
            return None

        tp = prices[-period:]  # Typical Price (simplified)
        sma = np.mean(tp)
        mad = np.mean(np.abs(tp - sma))

        if mad == 0:
            return 0

        cci = (prices[-1] - sma) / (0.015 * mad)
        return cci


class AdvancedTickCollector:
    """Advanced Tick Collector mit Indicators"""

    def __init__(self):
        self.config = get_config()
        self.db = get_database('local')
        self.symbols = self.config.get_symbols()
        self.tick_queues = {symbol: Queue(maxsize=500) for symbol in self.symbols}
        self.is_running = False
        self.indicator_calc = IndicatorCalculator()
        self.stats = {symbol: {'collected': 0, 'written': 0} for symbol in self.symbols}
        self.current_tables = {}

    def _get_today_table(self, symbol):
        """Get today's table name for symbol"""
        return f"ticks_{symbol.lower()}_{date.today().strftime('%Y%m%d')}"

    def _ensure_table(self, symbol):
        """Ensure today's table exists for symbol"""
        table = self._get_today_table(symbol)
        if table not in self.current_tables:
            self.current_tables[symbol] = table

            # Schema matching remote server
            sql = f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id SERIAL PRIMARY KEY,
                    handelszeit TIMESTAMP WITH TIME ZONE,
                    systemzeit TIMESTAMP WITH TIME ZONE,
                    mt5_ts TIMESTAMP WITH TIME ZONE,
                    bid DOUBLE PRECISION,
                    ask DOUBLE PRECISION,
                    volume BIGINT,

                    -- Technical Indicators
                    ma14 DOUBLE PRECISION,
                    ma50 DOUBLE PRECISION,
                    ema14 DOUBLE PRECISION,
                    ema50 DOUBLE PRECISION,
                    wma14 DOUBLE PRECISION,
                    wma50 DOUBLE PRECISION,
                    rsi14 DOUBLE PRECISION,
                    rsi28 DOUBLE PRECISION,
                    macd_main DOUBLE PRECISION,
                    macd_signal DOUBLE PRECISION,
                    macd_hist DOUBLE PRECISION,
                    adx14 DOUBLE PRECISION,
                    atr14 DOUBLE PRECISION,
                    cci14 DOUBLE PRECISION,
                    momentum14 DOUBLE PRECISION,
                    stddev14 DOUBLE PRECISION,
                    bb_upper DOUBLE PRECISION,
                    bb_middle DOUBLE PRECISION,
                    bb_lower DOUBLE PRECISION
                );

                CREATE INDEX IF NOT EXISTS idx_{table}_ts ON {table} (mt5_ts);
            """

            try:
                self.db.execute(sql)
                logger.info(f"Table ready: {table}")
            except Exception as e:
                logger.error(f"Table creation error for {symbol}: {e}")

    def _collect_loop(self, symbol):
        """Collect ticks for one symbol"""
        logger.info(f"Starting collection for {symbol}...")

        while self.is_running:
            try:
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    # Add to indicator calculator
                    self.indicator_calc.add_price(symbol, tick.bid, tick.ask)

                    # Calculate indicators
                    indicators = self.indicator_calc.calculate_indicators(symbol)

                    tick_data = {
                        'handelszeit': datetime.fromtimestamp(tick.time),
                        'systemzeit': datetime.now(),
                        'mt5_ts': datetime.fromtimestamp(tick.time),
                        'bid': float(tick.bid),
                        'ask': float(tick.ask),
                        'volume': int(tick.volume),
                        **indicators  # Add all calculated indicators
                    }

                    try:
                        self.tick_queues[symbol].put(tick_data, block=False)
                        self.stats[symbol]['collected'] += 1
                    except:
                        pass  # Queue full

                time.sleep(0.1)  # 10 ticks/second max per symbol

            except Exception as e:
                logger.error(f"Collection error for {symbol}: {e}")
                time.sleep(1)

    def _write_loop(self, symbol):
        """Write ticks for one symbol"""
        logger.info(f"Starting write loop for {symbol}...")
        batch = []
        last_write = time.time()

        while self.is_running or not self.tick_queues[symbol].empty():
            try:
                # Get tick from queue
                try:
                    tick = self.tick_queues[symbol].get(timeout=1)
                    batch.append(tick)
                except:
                    pass

                # Write batch
                now = time.time()
                should_write = len(batch) >= 50 or (len(batch) > 0 and now - last_write > 10)

                if should_write:
                    self._ensure_table(symbol)
                    table = self.current_tables[symbol]

                    # Build dynamic SQL based on available fields
                    if batch:
                        columns = list(batch[0].keys())
                        placeholders = ', '.join(['%s'] * len(columns))
                        column_str = ', '.join(columns)

                        sql = f"""
                            INSERT INTO {table} ({column_str})
                            VALUES ({placeholders})
                        """

                        values = [tuple(tick[col] for col in columns) for tick in batch]

                        try:
                            self.db.execute_many(sql, values)
                            self.stats[symbol]['written'] += len(batch)
                            logger.info(f"[{symbol}] Wrote {len(batch)} ticks to {table}")
                        except Exception as e:
                            logger.error(f"[{symbol}] Write error: {e}")

                        batch = []
                        last_write = now

            except Exception as e:
                logger.error(f"[{symbol}] Write loop error: {e}")
                time.sleep(1)

    def start(self):
        """Start collecting for all symbols"""
        self.is_running = True

        # Start collection thread for each symbol
        for symbol in self.symbols:
            threading.Thread(target=self._collect_loop, args=(symbol,), daemon=True).start()
            threading.Thread(target=self._write_loop, args=(symbol,), daemon=True).start()

        logger.info(f"Started collecting {len(self.symbols)} symbols with indicators")

    def stop(self):
        """Stop collecting"""
        self.is_running = False
        logger.info(f"Stats: {self.stats}")


def main():
    """Main function"""
    logger.info("=" * 70)
    logger.info("ADVANCED TICK COLLECTOR V2 - With Indicators")
    logger.info("=" * 70)

    try:
        if not mt5.initialize():
            logger.error("MT5 not available!")
            return

        account_info = mt5.account_info()
        if not account_info:
            logger.error("MT5 not logged in!")
            mt5.shutdown()
            return

        logger.info(f"Connected to MT5: {account_info.login}")

        collector = AdvancedTickCollector()
        collector.start()

        logger.info("Collecting ticks with indicators... Press Ctrl+C to stop")

        while True:
            time.sleep(30)
            # Print stats
            total_collected = sum(s['collected'] for s in collector.stats.values())
            total_written = sum(s['written'] for s in collector.stats.values())
            logger.info(f"Total: Collected={total_collected}, Written={total_written}")

    except KeyboardInterrupt:
        logger.info("Stopping...")
        if 'collector' in locals():
            collector.stop()
            time.sleep(3)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Tick Collector V2 stopped")

if __name__ == '__main__':
    main()

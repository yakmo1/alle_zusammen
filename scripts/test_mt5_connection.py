"""
MT5 Connection Test Script
Testet die Verbindung zu MetaTrader 5
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import MetaTrader5 as mt5

from src.utils.config_loader import get_config
from src.utils.logger import get_logger, log_exception

logger = get_logger('test_mt5')


def test_mt5_connection():
    """Testet MT5 Verbindung"""

    print("=" * 60)
    print("MetaTrader 5 Connection Test")
    print("=" * 60)

    try:
        # Config laden
        config = get_config()
        mt5_config = config.get_mt5_config()

        print("\n### MT5 Configuration ###")
        print(f"Server: {mt5_config['server']}")
        print(f"Login: {mt5_config['login']}")
        print(f"Path: {mt5_config.get('path', 'N/A')}")

        # MT5 initialisieren
        print("\n### Initializing MT5 ###")
        if not mt5.initialize(path=mt5_config.get('path')):
            error = mt5.last_error()
            print(f"✗ MT5 initialization failed: {error}")
            return False

        print("✓ MT5 initialized")

        # Login
        print("\n### Logging in ###")
        login_result = mt5.login(
            login=mt5_config['login'],
            password=mt5_config['password'],
            server=mt5_config['server']
        )

        if not login_result:
            error = mt5.last_error()
            print(f"✗ Login failed: {error}")
            mt5.shutdown()
            return False

        print("✓ Login successful")

        # Account Info
        print("\n### Account Information ###")
        account_info = mt5.account_info()
        if account_info:
            print(f"Name: {account_info.name}")
            print(f"Login: {account_info.login}")
            print(f"Server: {account_info.server}")
            print(f"Balance: {account_info.balance:.2f} {account_info.currency}")
            print(f"Equity: {account_info.equity:.2f} {account_info.currency}")
            print(f"Margin: {account_info.margin:.2f} {account_info.currency}")
            print(f"Free Margin: {account_info.margin_free:.2f} {account_info.currency}")
            print(f"Leverage: 1:{account_info.leverage}")
            print(f"Trade Allowed: {account_info.trade_allowed}")
        else:
            print("✗ Could not get account info")

        # Terminal Info
        print("\n### Terminal Information ###")
        terminal_info = mt5.terminal_info()
        if terminal_info:
            print(f"Terminal: {terminal_info.name}")
            print(f"Company: {terminal_info.company}")
            print(f"Path: {terminal_info.path}")
            print(f"Build: {terminal_info.build}")
            print(f"Connected: {terminal_info.connected}")
            print(f"Trade Allowed: {terminal_info.trade_allowed}")
        else:
            print("✗ Could not get terminal info")

        # Test Symbols
        print("\n### Testing Symbols ###")
        symbols = config.get_symbols()

        for symbol in symbols:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                print(f"\n{symbol}:")
                print(f"  Description: {symbol_info.description}")
                print(f"  Point: {symbol_info.point}")
                print(f"  Digits: {symbol_info.digits}")
                print(f"  Spread: {symbol_info.spread}")
                print(f"  Bid: {symbol_info.bid}")
                print(f"  Ask: {symbol_info.ask}")
                print(f"  Volume Min: {symbol_info.volume_min}")
                print(f"  Volume Max: {symbol_info.volume_max}")
                print(f"  Volume Step: {symbol_info.volume_step}")
                print(f"  Trade Allowed: {symbol_info.trade_mode}")

                # Enable symbol if not visible
                if not symbol_info.visible:
                    print(f"  ⚠ Symbol not visible, enabling...")
                    if mt5.symbol_select(symbol, True):
                        print(f"  ✓ Symbol enabled")
                    else:
                        print(f"  ✗ Failed to enable symbol")
            else:
                print(f"✗ {symbol}: Not available")

        # Test Tick Data
        print("\n### Testing Tick Data ###")
        test_symbol = symbols[0]
        print(f"Fetching latest tick for {test_symbol}...")

        tick = mt5.symbol_info_tick(test_symbol)
        if tick:
            print(f"  Time: {datetime.fromtimestamp(tick.time)}")
            print(f"  Bid: {tick.bid}")
            print(f"  Ask: {tick.ask}")
            print(f"  Last: {tick.last}")
            print(f"  Volume: {tick.volume}")
            print(f"✓ Tick data received")
        else:
            print("✗ Could not get tick data")

        # Test Historical Data
        print("\n### Testing Historical Data ###")
        from datetime import timedelta

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)

        print(f"Fetching 1 hour of M1 bars for {test_symbol}...")

        rates = mt5.copy_rates_range(
            test_symbol,
            mt5.TIMEFRAME_M1,
            start_time,
            end_time
        )

        if rates is not None and len(rates) > 0:
            print(f"✓ Received {len(rates)} bars")
            print(f"  First bar: {datetime.fromtimestamp(rates[0]['time'])}")
            print(f"  Last bar: {datetime.fromtimestamp(rates[-1]['time'])}")
            print(f"  Sample bar: O={rates[-1]['open']}, H={rates[-1]['high']}, L={rates[-1]['low']}, C={rates[-1]['close']}")
        else:
            print("✗ Could not get historical data")

        # Check Open Positions
        print("\n### Open Positions ###")
        positions = mt5.positions_get()
        if positions is not None:
            if len(positions) > 0:
                print(f"Found {len(positions)} open positions:")
                for pos in positions:
                    print(f"  {pos.ticket}: {pos.type} {pos.volume} {pos.symbol} @ {pos.price_open}")
            else:
                print("No open positions")
        else:
            print("✗ Could not get positions")

        # Check Orders
        print("\n### Open Orders ###")
        orders = mt5.orders_get()
        if orders is not None:
            if len(orders) > 0:
                print(f"Found {len(orders)} open orders:")
                for order in orders:
                    print(f"  {order.ticket}: {order.type} {order.volume_current} {order.symbol} @ {order.price_open}")
            else:
                print("No open orders")
        else:
            print("✗ Could not get orders")

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)

        # Shutdown
        mt5.shutdown()
        print("\n✓ MT5 connection closed")

        return True

    except Exception as e:
        log_exception(logger, e, "MT5 test failed")
        print(f"\n✗ ERROR: {e}")
        mt5.shutdown()
        return False


if __name__ == "__main__":
    success = test_mt5_connection()
    sys.exit(0 if success else 1)

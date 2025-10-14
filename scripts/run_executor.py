"""
Order Executor Runner
Führt automatisch Signals aus und überwacht Trades
"""

import sys
from pathlib import Path
import time
import signal as sig

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.order_executor import OrderExecutor
from src.core.signal_generator import SignalGenerator
from src.core.trade_monitor import TradeMonitor
from src.utils.logger import get_logger
import argparse


def signal_handler(signal, frame):
    """Handle Ctrl+C"""
    print("\nShutting down order executor...")
    sys.exit(0)


def main():
    """Main Function"""
    parser = argparse.ArgumentParser(description='Run Order Executor')
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Signal check interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='local',
        choices=['local', 'remote'],
        help='Database type (default: local)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no real orders)'
    )

    args = parser.parse_args()

    # Setup signal handler
    sig.signal(sig.SIGINT, signal_handler)

    logger = get_logger('ExecutorRunner')
    logger.info("=" * 70)
    logger.info("ORDER EXECUTOR & TRADE MONITOR")
    logger.info("=" * 70)

    if args.dry_run:
        logger.warning("*** DRY RUN MODE - NO REAL ORDERS ***")

    # Initialize components
    generator = SignalGenerator(db_type=args.db)
    executor = OrderExecutor(db_type=args.db, dry_run=args.dry_run)
    monitor = TradeMonitor(executor, db_type=args.db)

    # Start trade monitor
    monitor.start()

    logger.info(f"Signal check interval: {args.interval}s")
    logger.info("Press Ctrl+C to stop\n")

    try:
        while True:
            # Get active signals
            active_signals = generator.get_active_signals()

            if active_signals:
                logger.info(f"Found {len(active_signals)} active signals")

                for signal in active_signals:
                    # Execute signal
                    result = executor.execute_signal(signal)

                    if result:
                        logger.info(
                            f"✓ Order executed: {signal['symbol']} {signal['signal']} "
                            f"Ticket: {result['ticket']}"
                        )
                    else:
                        logger.warning(f"✗ Order failed: {signal['symbol']}")

            # Sleep
            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("\nStopping order executor...")
        monitor.stop()
        logger.info("Order executor stopped")


if __name__ == "__main__":
    main()

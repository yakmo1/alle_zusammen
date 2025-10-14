"""
Signal Generator Runner
Kontinuierlich Signals generieren
"""

import sys
from pathlib import Path
import time
import signal as sig

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.signal_generator import SignalGenerator
from src.utils.logger import get_logger
import argparse


def signal_handler(signal, frame):
    """Handle Ctrl+C"""
    print("\nShutting down signal generator...")
    sys.exit(0)


def main():
    """Main Function"""
    parser = argparse.ArgumentParser(description='Run Signal Generator')
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Signal generation interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='local',
        choices=['local', 'remote'],
        help='Database type (default: local)'
    )

    args = parser.parse_args()

    # Setup signal handler
    sig.signal(sig.SIGINT, signal_handler)

    logger = get_logger('SignalRunner')
    logger.info("=" * 70)
    logger.info("SIGNAL GENERATOR")
    logger.info("=" * 70)

    # Initialize generator
    generator = SignalGenerator(db_type=args.db)

    logger.info(f"Signal generation interval: {args.interval}s")
    logger.info("Press Ctrl+C to stop\n")

    try:
        while True:
            # Generate signals for all symbols
            signals = generator.generate_signals_all_symbols()

            if signals:
                logger.info(f"✓ Generated {len(signals)} signals")
                for signal in signals:
                    logger.info(
                        f"  {signal['symbol']}: {signal['signal']} @ {signal['entry_price']:.5f} "
                        f"(Confidence: {signal['confidence']:.3f})"
                    )
            else:
                logger.info("No signals generated (insufficient confidence or no predictions)")

            # Sleep
            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("\nSignal generator stopped")


if __name__ == "__main__":
    main()

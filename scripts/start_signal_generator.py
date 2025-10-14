"""
Signal Generator Service - Phase 3
Continuously generates and filters trading signals using ML models
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import MetaTrader5 as mt5
import time
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.signals.signal_generator import SignalGenerator
from src.signals.signal_filter import SignalFilter

logger = get_logger('SignalGeneratorService')


def main():
    """Main service loop"""
    logger.info("=" * 70)
    logger.info("SIGNAL GENERATOR SERVICE - Phase 3")
    logger.info("=" * 70)

    # Initialize MT5
    if not mt5.initialize():
        logger.error("MT5 initialization failed")
        return

    logger.info(f"MT5 initialized - Account: {mt5.account_info().login}")

    # Load config
    config = get_config()
    symbols = config.get_symbols()

    # Initialize signal generator and filter
    signal_generator = SignalGenerator(
        model_dir='models',
        confidence_threshold=0.70,  # 70% confidence required
        max_signals_per_hour=10
    )

    signal_filter = SignalFilter(
        max_positions_per_symbol=1,
        max_total_positions=3,
        max_daily_loss=500.0,  # $500 max daily loss
        max_drawdown_pct=10.0,  # 10% max drawdown
        max_spread_pips=2.0,
        min_confidence=0.70
    )

    # Paper trading mode (set to False for live trading)
    PAPER_TRADING = True

    if PAPER_TRADING:
        logger.warning("=" * 70)
        logger.warning("PAPER TRADING MODE - No real orders will be placed")
        logger.warning("=" * 70)
    else:
        logger.warning("=" * 70)
        logger.warning("LIVE TRADING MODE - Real orders will be placed!")
        logger.warning("=" * 70)
        time.sleep(5)  # Give time to cancel if mistake

    logger.info(f"Monitoring {len(symbols)} symbols: {', '.join(symbols)}")
    logger.info("Signal generation interval: 60 seconds")

    iteration = 0

    try:
        while True:
            iteration += 1
            logger.info(f"--- Iteration {iteration} - {datetime.now()} ---")

            # Generate signals for all symbols
            signals = signal_generator.generate_signals(
                symbols=symbols,
                paper_trading=PAPER_TRADING
            )

            if signals:
                logger.info(f"Generated {len(signals)} raw signals")

                # Filter signals
                filtered_signals = signal_filter.filter_signals(signals)

                if filtered_signals:
                    logger.info(f"Passed filters: {len(filtered_signals)} signals")

                    for signal in filtered_signals:
                        logger.info(
                            f"SIGNAL: {signal['symbol']} {signal['signal']} "
                            f"@ {signal['last_close']} "
                            f"(confidence: {signal['confidence']:.2%}, "
                            f"model: {signal['model']})"
                        )

                        # TODO Phase 4: Send to Auto Trader for execution
                        if not PAPER_TRADING:
                            logger.info("  -> Would execute in live mode")
                else:
                    logger.info("No signals passed filters")
            else:
                logger.debug("No signals generated this iteration")

            # Sleep before next iteration
            time.sleep(60)  # Check every 60 seconds

    except KeyboardInterrupt:
        logger.info("Stopping Signal Generator Service...")

    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        import traceback
        traceback.print_exc()

    finally:
        mt5.shutdown()
        logger.info("Signal Generator Service stopped")


if __name__ == '__main__':
    main()

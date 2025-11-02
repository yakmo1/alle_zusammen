"""
Inference Script
Führt ML Predictions in Real-time aus
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.inference_engine import InferenceEngine
from src.utils.logger import get_logger
import argparse
import signal


def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    print("\nShutting down...")
    sys.exit(0)


def main():
    """Main Function"""
    parser = argparse.ArgumentParser(description='Run ML Inference Engine')
    parser.add_argument(
        '--symbol',
        type=str,
        help='Single symbol to predict (default: all)'
    )
    parser.add_argument(
        '--timeframe',
        type=str,
        help='Single timeframe to predict (default: all)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='Prediction interval in seconds (default: 10)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='local',
        choices=['local', 'remote'],
        help='Database type (default: local)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (default: continuous)'
    )

    args = parser.parse_args()

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)

    logger = get_logger('Inference')
    logger.info("=" * 70)
    logger.info("ML INFERENCE ENGINE")
    logger.info("=" * 70)

    # Initialize engine
    engine = InferenceEngine(db_type=args.db)
    engine.prediction_interval = args.interval

    # Load models
    symbols = [args.symbol] if args.symbol else None
    timeframes = [args.timeframe] if args.timeframe else None

    logger.info("Loading models...")
    engine.load_models(symbols=symbols, timeframes=timeframes)

    if not engine.models:
        logger.error("No models loaded! Please train models first using train_models.py")
        sys.exit(1)

    logger.info(f"Loaded {len(engine.models)} models")

    if args.once:
        # Run once
        logger.info("\nMaking predictions...")

        for symbol in (symbols or engine.symbols):
            for timeframe in (timeframes or engine.timeframes):
                predictions = engine.predict_all_horizons(symbol, timeframe)

                if predictions:
                    logger.info(f"\n{symbol} {timeframe}:")
                    for pred in predictions:
                        logger.info(
                            f"  {pred['horizon']}s: "
                            f"{pred['current_price']:.5f} -> {pred['predicted_price']:.5f} "
                            f"({pred['price_change_pct']:+.3f}%) "
                            f"[{pred['signal']}] "
                            f"Confidence: {pred['confidence']:.3f}"
                        )

        logger.info("\n✓ Predictions complete!")

    else:
        # Run continuously
        logger.info(f"\nStarting continuous predictions (interval: {args.interval}s)...")
        logger.info("Press Ctrl+C to stop\n")

        try:
            engine.start()

            # Keep running
            while engine.is_running:
                import time
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\nStopping inference engine...")
            engine.stop()

    logger.info("\n" + "=" * 70)
    logger.info("Inference engine stopped")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

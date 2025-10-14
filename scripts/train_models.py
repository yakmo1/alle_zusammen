"""
Model Training Script
Trainiert alle ML-Models für das Trading System
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.model_trainer import ModelTrainer
from src.utils.logger import get_logger
import argparse


def main():
    """Main Function"""
    parser = argparse.ArgumentParser(description='Train ML Models')
    parser.add_argument(
        '--symbol',
        type=str,
        help='Single symbol to train (default: all)'
    )
    parser.add_argument(
        '--timeframe',
        type=str,
        help='Single timeframe to train (default: all)'
    )
    parser.add_argument(
        '--horizon',
        type=int,
        help='Single horizon to train (default: all)'
    )
    parser.add_argument(
        '--algorithm',
        type=str,
        choices=['xgboost', 'lightgbm'],
        help='Algorithm to use (default: both)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='local',
        choices=['local', 'remote'],
        help='Database type (default: local)'
    )

    args = parser.parse_args()

    logger = get_logger('TrainModels')
    logger.info("=" * 70)
    logger.info("ML MODEL TRAINING")
    logger.info("=" * 70)

    # Initialize trainer
    trainer = ModelTrainer(db_type=args.db)

    # Determine what to train
    if args.symbol and args.timeframe and args.horizon and args.algorithm:
        # Train single model
        logger.info(f"Training single model: {args.symbol} {args.timeframe} {args.horizon}s {args.algorithm}")

        model_info = trainer.train_model(
            symbol=args.symbol,
            timeframe=args.timeframe,
            horizon=args.horizon,
            algorithm=args.algorithm
        )

        if model_info:
            logger.info("✓ Training successful!")
            logger.info("\nMetrics:")
            for key, value in model_info['metrics'].items():
                logger.info(f"  {key}: {value:.6f}")
        else:
            logger.error("✗ Training failed!")
            sys.exit(1)

    else:
        # Train all models
        symbols = [args.symbol] if args.symbol else None
        timeframes = [args.timeframe] if args.timeframe else None

        logger.info("Training all models...")
        logger.info(f"Symbols: {symbols or 'all'}")
        logger.info(f"Timeframes: {timeframes or 'all'}")
        logger.info(f"Horizons: {trainer.horizons}")
        logger.info(f"Algorithms: {[args.algorithm] if args.algorithm else trainer.algorithms}")
        logger.info("")

        # Override algorithms if specified
        if args.algorithm:
            trainer.algorithms = [args.algorithm]

        results = trainer.train_all_models(symbols=symbols, timeframes=timeframes)

        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("TRAINING SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total models: {results['total']}")
        logger.info(f"Successful: {len(results['successful'])}")
        logger.info(f"Failed: {len(results['failed'])}")
        logger.info(f"Duration: {results['duration']:.0f}s")
        logger.info("")

        if results['successful']:
            logger.info("Top 5 Models by R² Score:")
            sorted_models = sorted(
                results['successful'],
                key=lambda x: x['metrics']['test_r2'],
                reverse=True
            )[:5]

            for i, model in enumerate(sorted_models, 1):
                logger.info(
                    f"  {i}. {model['symbol']} {model['timeframe']} "
                    f"{model['horizon']}s {model['algorithm']}: "
                    f"R²={model['metrics']['test_r2']:.4f}"
                )

        if results['failed']:
            logger.warning(f"\n{len(results['failed'])} models failed to train")

    logger.info("\n" + "=" * 70)
    logger.info("Training complete!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

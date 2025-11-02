"""
Automated Model Retraining
Führt automatisches nächtliches Model Retraining durch
"""

import sys
from pathlib import Path
import schedule
import time
from datetime import datetime, time as dt_time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.model_trainer import ModelTrainer
from src.utils.logger import get_logger
import argparse


class AutomatedRetrainer:
    """Automated Model Retraining System"""

    def __init__(self, db_type: str = 'local'):
        """
        Initialize Automated Retrainer

        Args:
            db_type: Database type
        """
        self.logger = get_logger(self.__class__.__name__)
        self.trainer = ModelTrainer(db_type=db_type)
        self.db_type = db_type

        # Configuration
        self.retrain_time = dt_time(hour=2, minute=0)  # 2 AM
        self.retrain_days = ['sunday']  # Weekly on Sunday
        self.min_data_days = 7  # Minimum 7 days of data required

    def should_retrain(self) -> bool:
        """
        Check if retraining should occur

        Returns:
            True if retraining should occur
        """
        now = datetime.now()

        # Check day of week
        if now.strftime('%A').lower() not in self.retrain_days:
            self.logger.info(f"Not a training day (today: {now.strftime('%A')})")
            return False

        # Check time
        current_time = now.time()
        if current_time < self.retrain_time:
            self.logger.info(f"Not time to retrain yet (current: {current_time}, scheduled: {self.retrain_time})")
            return False

        # Check if enough data is available
        if not self._check_data_availability():
            self.logger.warning("Insufficient data for retraining")
            return False

        return True

    def _check_data_availability(self) -> bool:
        """
        Check if enough data is available for training

        Returns:
            True if sufficient data is available
        """
        try:
            from src.data.database_manager import get_database

            db = get_database(self.db_type)

            # Check if we have data from last N days
            query = """
                SELECT COUNT(DISTINCT DATE(timestamp)) as days_with_data
                FROM features
                WHERE timestamp >= NOW() - INTERVAL '{days} days'
            """.format(days=self.min_data_days)

            result = db.fetch_dict(query)

            if not result:
                return False

            days_with_data = result.get('days_with_data', 0)
            self.logger.info(f"Data availability: {days_with_data}/{self.min_data_days} days")

            return days_with_data >= self.min_data_days

        except Exception as e:
            self.logger.error(f"Error checking data availability: {e}")
            return False

    def retrain_models(self):
        """Execute model retraining"""
        self.logger.info("=" * 70)
        self.logger.info("AUTOMATED MODEL RETRAINING")
        self.logger.info("=" * 70)
        self.logger.info(f"Started at: {datetime.now()}")

        try:
            # Train all models
            results = self.trainer.train_all_models()

            # Log summary
            self.logger.info("\n" + "=" * 70)
            self.logger.info("RETRAINING SUMMARY")
            self.logger.info("=" * 70)
            self.logger.info(f"Total models: {results['total']}")
            self.logger.info(f"Successful: {len(results['successful'])}")
            self.logger.info(f"Failed: {len(results['failed'])}")
            self.logger.info(f"Duration: {results['duration']:.0f}s")

            # Log top models
            if results['successful']:
                self.logger.info("\nTop 10 Models by R² Score:")
                sorted_models = sorted(
                    results['successful'],
                    key=lambda x: x['metrics']['test_r2'],
                    reverse=True
                )[:10]

                for i, model in enumerate(sorted_models, 1):
                    self.logger.info(
                        f"  {i}. {model['symbol']} {model['timeframe']} "
                        f"{model['horizon']}s {model['algorithm']}: "
                        f"R²={model['metrics']['test_r2']:.4f}, "
                        f"RMSE={model['metrics']['test_rmse']:.6f}"
                    )

            # Check for failed models
            if results['failed']:
                self.logger.warning(f"\n{len(results['failed'])} models failed to train:")
                for failed in results['failed'][:5]:  # Show first 5
                    self.logger.warning(
                        f"  - {failed['symbol']} {failed['timeframe']} "
                        f"{failed['horizon']}s {failed['algorithm']}"
                    )

            # Save retraining log
            self._save_retraining_log(results)

            self.logger.info("\n" + "=" * 70)
            self.logger.info(f"Retraining completed at: {datetime.now()}")
            self.logger.info("=" * 70)

            return results

        except Exception as e:
            self.logger.error(f"Error during retraining: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _save_retraining_log(self, results: dict):
        """
        Save retraining log to database

        Args:
            results: Retraining results
        """
        try:
            from src.data.database_manager import get_database

            db = get_database(self.db_type)

            import json
            insert_sql = """
                INSERT INTO system_logs
                    (timestamp, log_level, component, message, details)
                VALUES
                    (%s, %s, %s, %s, %s)
            """

            db.execute(insert_sql, (
                datetime.now(),
                'INFO',
                'AutomatedRetrainer',
                f"Model retraining completed: {len(results['successful'])}/{results['total']} successful",
                json.dumps({
                    'total': results['total'],
                    'successful': len(results['successful']),
                    'failed': len(results['failed']),
                    'duration': results['duration']
                })
            ))

            self.logger.info("Retraining log saved to database")

        except Exception as e:
            self.logger.error(f"Error saving retraining log: {e}")

    def run_scheduled(self):
        """Run automated retraining on schedule"""
        self.logger.info("Automated retraining scheduler started")
        self.logger.info(f"Schedule: {', '.join(self.retrain_days)} at {self.retrain_time}")

        # Schedule the job
        schedule.every().sunday.at(self.retrain_time.strftime("%H:%M")).do(self.retrain_models)

        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

            except KeyboardInterrupt:
                self.logger.info("\nScheduler stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler: {e}")
                time.sleep(60)

    def run_once(self):
        """Run retraining once immediately"""
        self.logger.info("Running one-time retraining...")
        return self.retrain_models()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Automated Model Retraining')
    parser.add_argument(
        '--mode',
        type=str,
        default='scheduled',
        choices=['scheduled', 'once'],
        help='Run mode: scheduled (default) or once'
    )
    parser.add_argument(
        '--db',
        type=str,
        default='local',
        choices=['local', 'remote'],
        help='Database type (default: local)'
    )
    parser.add_argument(
        '--day',
        type=str,
        help='Day of week for scheduled retraining (e.g., sunday, monday)'
    )
    parser.add_argument(
        '--time',
        type=str,
        help='Time for scheduled retraining (HH:MM format, e.g., 02:00)'
    )

    args = parser.parse_args()

    # Initialize retrainer
    retrainer = AutomatedRetrainer(db_type=args.db)

    # Override schedule if specified
    if args.day:
        retrainer.retrain_days = [args.day.lower()]

    if args.time:
        try:
            hour, minute = map(int, args.time.split(':'))
            retrainer.retrain_time = dt_time(hour=hour, minute=minute)
        except:
            print(f"Invalid time format: {args.time}. Using default.")

    # Run
    if args.mode == 'once':
        results = retrainer.run_once()
        if results:
            print("\n✓ Retraining completed successfully")
            sys.exit(0)
        else:
            print("\n✗ Retraining failed")
            sys.exit(1)
    else:
        # Scheduled mode
        print("=" * 70)
        print("AUTOMATED MODEL RETRAINING - SCHEDULER")
        print("=" * 70)
        print(f"Schedule: {', '.join(retrainer.retrain_days)} at {retrainer.retrain_time}")
        print(f"Database: {args.db}")
        print(f"Min data days: {retrainer.min_data_days}")
        print("\nPress Ctrl+C to stop\n")
        print("=" * 70)

        retrainer.run_scheduled()


if __name__ == "__main__":
    main()

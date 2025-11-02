"""
Data Quality Monitor
Überwacht Datenqualität und erkennt Probleme
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

from .logger import get_logger, log_exception
from .config_loader import get_config
from ..data.database_manager import get_database


class DataQualityMonitor:
    """Überwacht Datenqualität"""

    def __init__(self, db_type: str = 'local'):
        """
        Initialize Data Quality Monitor

        Args:
            db_type: Database type
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)

        # Thresholds
        self.min_ticks_per_minute = 50  # Minimum ticks pro Minute
        self.max_gap_minutes = 5  # Max Gap zwischen Ticks (Minuten)
        self.min_bars_per_day = 1000  # Minimum Bars pro Tag
        self.max_spread_pips = 5  # Maximum Spread (Pips)

    def check_tick_data_quality(
        self,
        symbol: str,
        hours: int = 1
    ) -> Dict[str, Any]:
        """
        Check tick data quality

        Args:
            symbol: Trading symbol
            hours: Hours to check back

        Returns:
            Quality report dictionary
        """
        try:
            from datetime import date
            today = date.today()
            table_name = f"ticks_{today.strftime('%Y%m%d')}"

            # Check if table exists
            if not self.db.table_exists(table_name):
                return {
                    'status': 'ERROR',
                    'message': f"Table {table_name} not found",
                    'issues': ['No tick data available']
                }

            # Get tick count
            query = f"""
                SELECT
                    COUNT(*) as tick_count,
                    MIN(timestamp) as first_tick,
                    MAX(timestamp) as last_tick,
                    AVG(ask - bid) as avg_spread
                FROM {table_name}
                WHERE symbol = %s
                  AND timestamp >= NOW() - INTERVAL '{hours} hours'
            """

            result = self.db.fetch_dict(query, (symbol,))

            if not result:
                return {
                    'status': 'ERROR',
                    'message': 'No data returned',
                    'issues': ['Query failed']
                }

            tick_count = result['tick_count']
            first_tick = result['first_tick']
            last_tick = result['last_tick']
            avg_spread = float(result['avg_spread'] or 0)

            issues = []
            warnings = []

            # Check tick count
            expected_min_ticks = hours * 60 * self.min_ticks_per_minute
            if tick_count < expected_min_ticks:
                issues.append(
                    f"Low tick count: {tick_count} (expected > {expected_min_ticks})"
                )

            # Check spread
            avg_spread_pips = avg_spread * 10000
            if avg_spread_pips > self.max_spread_pips:
                warnings.append(
                    f"High average spread: {avg_spread_pips:.1f} pips "
                    f"(threshold: {self.max_spread_pips} pips)"
                )

            # Check gaps
            gaps = self._detect_gaps(table_name, symbol, hours)
            if gaps:
                issues.extend([
                    f"Data gap: {gap['duration']} minutes at {gap['start_time']}"
                    for gap in gaps
                ])

            # Determine status
            if issues:
                status = 'WARNING' if tick_count > 0 else 'ERROR'
            else:
                status = 'OK'

            return {
                'status': status,
                'symbol': symbol,
                'tick_count': tick_count,
                'first_tick': first_tick,
                'last_tick': last_tick,
                'avg_spread_pips': avg_spread_pips,
                'issues': issues,
                'warnings': warnings,
                'hours_checked': hours
            }

        except Exception as e:
            log_exception(self.logger, e, f"Error checking tick quality for {symbol}")
            return {
                'status': 'ERROR',
                'message': str(e),
                'issues': [str(e)]
            }

    def _detect_gaps(
        self,
        table_name: str,
        symbol: str,
        hours: int
    ) -> List[Dict[str, Any]]:
        """
        Detect gaps in tick data

        Args:
            table_name: Tick table name
            symbol: Trading symbol
            hours: Hours to check

        Returns:
            List of gaps
        """
        try:
            query = f"""
                SELECT
                    timestamp,
                    LEAD(timestamp) OVER (ORDER BY timestamp) as next_timestamp
                FROM {table_name}
                WHERE symbol = %s
                  AND timestamp >= NOW() - INTERVAL '{hours} hours'
            """

            results = self.db.fetch_all_dict(query, (symbol,))

            gaps = []
            for row in results:
                if row['next_timestamp']:
                    gap_seconds = (row['next_timestamp'] - row['timestamp']).total_seconds()
                    gap_minutes = gap_seconds / 60

                    if gap_minutes > self.max_gap_minutes:
                        gaps.append({
                            'start_time': row['timestamp'],
                            'end_time': row['next_timestamp'],
                            'duration': gap_minutes
                        })

            return gaps

        except Exception as e:
            log_exception(self.logger, e, "Error detecting gaps")
            return []

    def check_bar_data_quality(
        self,
        symbol: str,
        timeframe: str,
        days: int = 1
    ) -> Dict[str, Any]:
        """
        Check bar data quality

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '1m', '5m')
            days: Days to check back

        Returns:
            Quality report dictionary
        """
        try:
            table_name = f"bars_{timeframe}"

            query = f"""
                SELECT
                    COUNT(*) as bar_count,
                    MIN(timestamp) as first_bar,
                    MAX(timestamp) as last_bar,
                    AVG(high - low) as avg_range,
                    AVG(volume) as avg_volume
                FROM {table_name}
                WHERE symbol = %s
                  AND timestamp >= NOW() - INTERVAL '{days} days'
            """

            result = self.db.fetch_dict(query, (symbol,))

            if not result:
                return {
                    'status': 'ERROR',
                    'message': 'No data returned',
                    'issues': ['Query failed']
                }

            bar_count = result['bar_count']
            avg_range = float(result['avg_range'] or 0)
            avg_volume = float(result['avg_volume'] or 0)

            issues = []

            # Check bar count
            expected_min_bars = days * self.min_bars_per_day
            if bar_count < expected_min_bars:
                issues.append(
                    f"Low bar count: {bar_count} (expected > {expected_min_bars})"
                )

            # Check for zero volume
            if avg_volume == 0:
                issues.append("Zero average volume detected")

            # Determine status
            status = 'OK' if not issues else 'WARNING'

            return {
                'status': status,
                'symbol': symbol,
                'timeframe': timeframe,
                'bar_count': bar_count,
                'avg_range_pips': avg_range * 10000,
                'avg_volume': avg_volume,
                'issues': issues,
                'days_checked': days
            }

        except Exception as e:
            log_exception(self.logger, e, f"Error checking bar quality for {symbol}")
            return {
                'status': 'ERROR',
                'message': str(e),
                'issues': [str(e)]
            }

    def check_feature_data_quality(
        self,
        symbol: str,
        timeframe: str,
        hours: int = 1
    ) -> Dict[str, Any]:
        """
        Check feature data quality

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            hours: Hours to check back

        Returns:
            Quality report dictionary
        """
        try:
            query = """
                SELECT
                    COUNT(*) as feature_count,
                    MIN(timestamp) as first_feature,
                    MAX(timestamp) as last_feature,
                    COUNT(CASE WHEN rsi_14 IS NULL THEN 1 END) as null_rsi_count,
                    COUNT(CASE WHEN macd IS NULL THEN 1 END) as null_macd_count
                FROM features
                WHERE symbol = %s
                  AND timeframe = %s
                  AND timestamp >= NOW() - INTERVAL '{hours} hours'
            """.format(hours=hours)

            result = self.db.fetch_dict(query, (symbol, timeframe))

            if not result:
                return {
                    'status': 'ERROR',
                    'message': 'No data returned',
                    'issues': ['Query failed']
                }

            feature_count = result['feature_count']
            null_rsi = result['null_rsi_count']
            null_macd = result['null_macd_count']

            issues = []

            # Check feature count
            if feature_count == 0:
                issues.append("No features calculated")

            # Check for NULL values
            if null_rsi > 0 or null_macd > 0:
                issues.append(f"NULL values detected: RSI={null_rsi}, MACD={null_macd}")

            # Determine status
            status = 'OK' if not issues else 'WARNING'

            return {
                'status': status,
                'symbol': symbol,
                'timeframe': timeframe,
                'feature_count': feature_count,
                'null_values': {
                    'rsi': null_rsi,
                    'macd': null_macd
                },
                'issues': issues,
                'hours_checked': hours
            }

        except Exception as e:
            log_exception(self.logger, e, f"Error checking feature quality for {symbol}")
            return {
                'status': 'ERROR',
                'message': str(e),
                'issues': [str(e)]
            }

    def generate_quality_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive quality report

        Returns:
            Quality report dictionary
        """
        self.logger.info("Generating data quality report...")

        symbols = self.config.get_symbols()
        timeframes = ['1m', '5m', '15m']

        report = {
            'timestamp': datetime.now().isoformat(),
            'tick_quality': {},
            'bar_quality': {},
            'feature_quality': {},
            'summary': {
                'total_issues': 0,
                'total_warnings': 0,
                'status': 'OK'
            }
        }

        # Check tick data
        for symbol in symbols:
            tick_report = self.check_tick_data_quality(symbol, hours=1)
            report['tick_quality'][symbol] = tick_report

            if tick_report['status'] == 'ERROR':
                report['summary']['total_issues'] += len(tick_report.get('issues', []))
            elif tick_report['status'] == 'WARNING':
                report['summary']['total_warnings'] += len(tick_report.get('issues', []))

        # Check bar data
        for symbol in symbols:
            report['bar_quality'][symbol] = {}
            for timeframe in timeframes:
                bar_report = self.check_bar_data_quality(symbol, timeframe, days=1)
                report['bar_quality'][symbol][timeframe] = bar_report

                if bar_report['status'] == 'WARNING':
                    report['summary']['total_warnings'] += len(bar_report.get('issues', []))

        # Check feature data
        for symbol in symbols:
            report['feature_quality'][symbol] = {}
            for timeframe in timeframes:
                feature_report = self.check_feature_data_quality(symbol, timeframe, hours=1)
                report['feature_quality'][symbol][timeframe] = feature_report

                if feature_report['status'] == 'WARNING':
                    report['summary']['total_warnings'] += len(feature_report.get('issues', []))

        # Determine overall status
        if report['summary']['total_issues'] > 0:
            report['summary']['status'] = 'ERROR'
        elif report['summary']['total_warnings'] > 0:
            report['summary']['status'] = 'WARNING'

        self.logger.info(f"Quality report generated: Status={report['summary']['status']}")

        return report


if __name__ == "__main__":
    # Test
    print("=== Data Quality Monitor Test ===\n")

    monitor = DataQualityMonitor()

    # Generate report
    print("Generating quality report...")
    report = monitor.generate_quality_report()

    print(f"\nOverall Status: {report['summary']['status']}")
    print(f"Total Issues: {report['summary']['total_issues']}")
    print(f"Total Warnings: {report['summary']['total_warnings']}")

    # Show tick quality
    print("\nTick Data Quality:")
    for symbol, quality in report['tick_quality'].items():
        print(f"  {symbol}: {quality['status']} ({quality.get('tick_count', 0)} ticks)")
        if quality.get('issues'):
            for issue in quality['issues']:
                print(f"    - {issue}")

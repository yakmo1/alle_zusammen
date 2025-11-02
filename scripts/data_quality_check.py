"""
Data Quality Validation
- Checks tick data quality
- Checks bar data quality
- Detects gaps, NULL values, anomalies
- Outputs quality score
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from datetime import datetime, timedelta, date
import pandas as pd
from src.utils.config_loader import get_config

def connect_db():
    """Connect to trading database"""
    return psycopg2.connect(
        host='localhost',
        port='5432',
        database='trading_db',
        user='mt5user',
        password='1234'
    )

def check_tick_quality(conn, symbol):
    """Check tick data quality for symbol"""
    today = date.today().strftime('%Y%m%d')
    table_name = f"ticks_{symbol.lower()}_{today}"

    cur = conn.cursor()

    # Check if table exists
    cur.execute(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = '{table_name}'
        )
    """)

    if not cur.fetchone()[0]:
        return {
            'exists': False,
            'error': f'Table {table_name} does not exist'
        }

    # Get basic stats
    cur.execute(f"""
        SELECT
            COUNT(*) as total_ticks,
            MIN(mt5_ts) as first_tick,
            MAX(mt5_ts) as last_tick,
            COUNT(DISTINCT DATE_TRUNC('minute', mt5_ts)) as unique_minutes
        FROM {table_name}
    """)

    stats = cur.fetchone()
    total_ticks, first_tick, last_tick, unique_minutes = stats

    if total_ticks == 0:
        return {
            'exists': True,
            'total_ticks': 0,
            'error': 'No ticks in table'
        }

    # Check for NULL values in critical fields
    cur.execute(f"""
        SELECT
            COUNT(*) FILTER (WHERE bid IS NULL) as null_bid,
            COUNT(*) FILTER (WHERE ask IS NULL) as null_ask,
            COUNT(*) FILTER (WHERE mt5_ts IS NULL) as null_timestamp
        FROM {table_name}
    """)

    null_bid, null_ask, null_ts = cur.fetchone()

    # Check for indicator coverage
    cur.execute(f"""
        SELECT
            COUNT(*) FILTER (WHERE rsi14 IS NOT NULL) as with_rsi,
            COUNT(*) FILTER (WHERE macd_main IS NOT NULL) as with_macd,
            COUNT(*) FILTER (WHERE bb_upper IS NOT NULL) as with_bb
        FROM {table_name}
    """)

    with_rsi, with_macd, with_bb = cur.fetchone()

    # Calculate time span
    if first_tick and last_tick:
        time_span = (last_tick - first_tick).total_seconds() / 60  # minutes
        expected_ticks_min = time_span * 6  # 6 symbols, ~1 tick/sec each = min 360 ticks/min
        expected_ticks_max = time_span * 60  # max 60 ticks/sec per symbol

        # Data completeness score
        completeness = min(100, (total_ticks / expected_ticks_min) * 100) if expected_ticks_min > 0 else 0
    else:
        time_span = 0
        completeness = 0

    # Indicator coverage percentage
    indicator_coverage = (with_rsi / total_ticks * 100) if total_ticks > 0 else 0

    # Quality score (0-100)
    quality_score = (
        (50 if null_bid == 0 and null_ask == 0 and null_ts == 0 else 25) +  # No NULLs in critical fields
        (min(25, completeness / 4)) +  # Data completeness
        (min(25, indicator_coverage / 4))  # Indicator coverage
    )

    cur.close()

    return {
        'exists': True,
        'symbol': symbol,
        'table': table_name,
        'total_ticks': total_ticks,
        'first_tick': first_tick,
        'last_tick': last_tick,
        'time_span_minutes': time_span,
        'unique_minutes': unique_minutes,
        'null_values': {
            'bid': null_bid,
            'ask': null_ask,
            'timestamp': null_ts
        },
        'indicators': {
            'with_rsi': with_rsi,
            'with_macd': with_macd,
            'with_bb': with_bb,
            'coverage_pct': round(indicator_coverage, 2)
        },
        'quality_score': round(quality_score, 2),
        'issues': []
    }

def check_bar_quality(conn, symbol):
    """Check bar data quality for symbol"""
    table_name = f"bars_{symbol.lower()}"

    cur = conn.cursor()

    # Check if table exists
    cur.execute(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = '{table_name}'
        )
    """)

    if not cur.fetchone()[0]:
        return {
            'exists': False,
            'error': f'Table {table_name} does not exist'
        }

    # Get stats per timeframe
    cur.execute(f"""
        SELECT
            timeframe,
            COUNT(*) as bar_count,
            MIN(timestamp) as first_bar,
            MAX(timestamp) as last_bar,
            COUNT(*) FILTER (WHERE rsi14 IS NOT NULL) as with_indicators
        FROM {table_name}
        GROUP BY timeframe
        ORDER BY timeframe
    """)

    timeframes = {}
    for row in cur.fetchall():
        tf, count, first, last, with_ind = row

        # Check for gaps in timeframe
        if first and last and count > 1:
            time_diff = (last - first).total_seconds()

            if tf == '1m':
                expected_bars = time_diff / 60
            elif tf == '5m':
                expected_bars = time_diff / 300
            elif tf == '15m':
                expected_bars = time_diff / 900
            elif tf == '1h':
                expected_bars = time_diff / 3600
            elif tf == '4h':
                expected_bars = time_diff / 14400
            else:
                expected_bars = count

            completeness = (count / max(1, expected_bars)) * 100
        else:
            completeness = 100

        indicator_pct = (with_ind / count * 100) if count > 0 else 0

        timeframes[tf] = {
            'bar_count': count,
            'first_bar': first,
            'last_bar': last,
            'completeness_pct': round(min(100, completeness), 2),
            'indicator_pct': round(indicator_pct, 2)
        }

    # Overall quality score
    if timeframes:
        avg_completeness = sum(tf['completeness_pct'] for tf in timeframes.values()) / len(timeframes)
        avg_indicators = sum(tf['indicator_pct'] for tf in timeframes.values()) / len(timeframes)
        quality_score = (avg_completeness * 0.6 + avg_indicators * 0.4)
    else:
        quality_score = 0

    cur.close()

    return {
        'exists': True,
        'symbol': symbol,
        'table': table_name,
        'timeframes': timeframes,
        'quality_score': round(quality_score, 2)
    }

def generate_report(tick_results, bar_results):
    """Generate quality report"""
    print("\n" + "=" * 80)
    print("DATA QUALITY VALIDATION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    print("\n### TICK DATA QUALITY ###\n")

    for result in tick_results:
        symbol = result.get('symbol', 'Unknown')
        print(f"\n[{symbol}]")

        if not result.get('exists'):
            print(f"  ERROR: {result.get('error')}")
            continue

        if result.get('total_ticks', 0) == 0:
            print(f"  WARNING: {result.get('error', 'No data')}")
            continue

        print(f"  Total Ticks: {result['total_ticks']:,}")
        print(f"  Time Range: {result['first_tick']} to {result['last_tick']}")
        print(f"  Time Span: {result['time_span_minutes']:.1f} minutes")
        print(f"  Unique Minutes: {result['unique_minutes']}")

        nulls = result['null_values']
        if nulls['bid'] > 0 or nulls['ask'] > 0 or nulls['timestamp'] > 0:
            print(f"  NULL Values: bid={nulls['bid']}, ask={nulls['ask']}, ts={nulls['timestamp']}")

        ind = result['indicators']
        print(f"  Indicator Coverage: {ind['coverage_pct']:.1f}% ({ind['with_rsi']:,} ticks)")

        score = result['quality_score']
        if score >= 90:
            status = "EXCELLENT"
        elif score >= 75:
            status = "GOOD"
        elif score >= 60:
            status = "ACCEPTABLE"
        else:
            status = "POOR"

        print(f"  Quality Score: {score:.1f}/100 [{status}]")

    print("\n### BAR DATA QUALITY ###\n")

    for result in bar_results:
        symbol = result.get('symbol', 'Unknown')
        print(f"\n[{symbol}]")

        if not result.get('exists'):
            print(f"  ERROR: {result.get('error')}")
            continue

        timeframes = result.get('timeframes', {})
        if not timeframes:
            print(f"  WARNING: No bars generated yet")
            continue

        for tf, stats in timeframes.items():
            print(f"  {tf:5s}: {stats['bar_count']:4d} bars | " +
                  f"Completeness: {stats['completeness_pct']:5.1f}% | " +
                  f"Indicators: {stats['indicator_pct']:5.1f}%")

        score = result['quality_score']
        if score >= 90:
            status = "EXCELLENT"
        elif score >= 75:
            status = "GOOD"
        elif score >= 60:
            status = "ACCEPTABLE"
        else:
            status = "POOR"

        print(f"  Overall Quality Score: {score:.1f}/100 [{status}]")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    tick_scores = [r['quality_score'] for r in tick_results if r.get('quality_score')]
    bar_scores = [r['quality_score'] for r in bar_results if r.get('quality_score')]

    if tick_scores:
        avg_tick_score = sum(tick_scores) / len(tick_scores)
        print(f"Average Tick Data Quality: {avg_tick_score:.1f}/100")

    if bar_scores:
        avg_bar_score = sum(bar_scores) / len(bar_scores)
        print(f"Average Bar Data Quality: {avg_bar_score:.1f}/100")

    if tick_scores and bar_scores:
        overall_score = (avg_tick_score + avg_bar_score) / 2
        print(f"\nOVERALL DATA QUALITY: {overall_score:.1f}/100")

        if overall_score >= 90:
            print("Status: EXCELLENT - Ready for ML training")
        elif overall_score >= 75:
            print("Status: GOOD - Suitable for ML training")
        elif overall_score >= 60:
            print("Status: ACCEPTABLE - Can be used with caution")
        else:
            print("Status: POOR - More data collection needed")

    print("=" * 80 + "\n")

def main():
    """Main function"""
    print("Starting Data Quality Validation...")

    # Connect to database
    conn = connect_db()

    # Get symbols from config
    config = get_config()
    symbols = config.get_symbols()

    # Check tick quality
    tick_results = []
    for symbol in symbols:
        try:
            result = check_tick_quality(conn, symbol)
            tick_results.append(result)
        except Exception as e:
            print(f"Error checking ticks for {symbol}: {e}")
            tick_results.append({
                'symbol': symbol,
                'exists': False,
                'error': str(e)
            })

    # Check bar quality
    bar_results = []
    for symbol in symbols:
        try:
            result = check_bar_quality(conn, symbol)
            bar_results.append(result)
        except Exception as e:
            print(f"Error checking bars for {symbol}: {e}")
            bar_results.append({
                'symbol': symbol,
                'exists': False,
                'error': str(e)
            })

    conn.close()

    # Generate report
    generate_report(tick_results, bar_results)

if __name__ == '__main__':
    main()

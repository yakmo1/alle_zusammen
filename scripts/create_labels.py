# -*- coding: utf-8 -*-
"""
Create Labels from Bar Data
- Loads bar data from database
- Generates multi-horizon labels
- Analyzes label distribution
- Saves labeled data for training
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.utils.config_loader import get_config
from src.data.database_manager import get_database
from src.ml.label_engineering import LabelEngineer
from datetime import datetime


def load_bar_data(db, symbol: str, timeframe: str = '1m', limit: int = None):
    """Load bar data from database"""
    table = f"bars_{symbol.lower()}"

    sql = f"""
        SELECT
            timestamp,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            tick_count,
            rsi14,
            macd_main,
            bb_upper,
            bb_lower,
            atr14
        FROM {table}
        WHERE timeframe = %s
        ORDER BY timestamp ASC
    """

    if limit:
        sql += f" LIMIT {limit}"

    try:
        result = db.fetch_all(sql, (timeframe,))

        if not result:
            return None

        columns = ['timestamp', 'timeframe', 'open', 'high', 'low', 'close',
                  'volume', 'tick_count', 'rsi14', 'macd_main',
                  'bb_upper', 'bb_lower', 'atr14']

        df = pd.DataFrame(result, columns=columns)
        return df

    except Exception as e:
        print(f"Error loading bars for {symbol}: {e}")
        return None


def create_labels_for_symbol(symbol: str, timeframe: str = '1m'):
    """Create labels for a single symbol"""
    print(f"\n{'='*70}")
    print(f"Creating labels for {symbol} ({timeframe})")
    print(f"{'='*70}")

    db = get_database('local')

    # Load bar data
    df = load_bar_data(db, symbol, timeframe)

    if df is None or len(df) == 0:
        print(f"No data available for {symbol}")
        return None

    print(f"Loaded {len(df)} bars")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()

    # Initialize label engineer
    engineer = LabelEngineer(pip_value=0.0001, min_profit_pips=3.0)

    # Define horizons based on config
    config = get_config()
    target_minutes = [0.5, 1.0, 3.0, 5.0, 10.0]  # 30s, 60s, 3min, 5min, 10min

    # Create labels
    df_labeled = engineer.create_labels_from_timeframe(df, timeframe, target_minutes)

    # Analyze distribution
    label_cols = [col for col in df_labeled.columns if col.startswith('label_h')]
    stats = engineer.analyze_label_distribution(df_labeled, label_cols)

    print("Label Distribution:")
    print(f"{'Horizon':<15} {'Total':<8} {'UP%':<8} {'DOWN%':<8} {'Balance':<8}")
    print("-" * 55)

    for i, col in enumerate(label_cols):
        if col in stats:
            s = stats[col]
            horizon_name = f"{target_minutes[i]:.1f} min"
            print(f"{horizon_name:<15} {s['total']:<8} {s['up_pct']:<8.1f} "
                  f"{s['down_pct']:<8.1f} {s['balance']:<8.2f}")

    print()

    # Check for severe class imbalance
    severe_imbalance = []
    for col, stat in stats.items():
        if stat['balance'] < 0.3:  # Less than 30% balance
            severe_imbalance.append(col)

    if severe_imbalance:
        print(f"WARNING: Severe class imbalance detected in: {', '.join(severe_imbalance)}")
        print("   Consider:")
        print("   - Reducing min_profit_pips threshold")
        print("   - Using class balancing techniques")
        print("   - Collecting more diverse market data")
        print()

    return df_labeled


def create_labels_for_all_symbols(timeframe: str = '1m'):
    """Create labels for all configured symbols"""
    print("\n" + "="*70)
    print("LABEL GENERATION FOR ALL SYMBOLS")
    print("="*70)
    print(f"Timeframe: {timeframe}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    config = get_config()
    symbols = config.get_symbols()

    results = {}

    for symbol in symbols:
        df_labeled = create_labels_for_symbol(symbol, timeframe)
        if df_labeled is not None:
            results[symbol] = df_labeled

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    total_samples = sum(len(df) for df in results.values())
    print(f"Total symbols processed: {len(results)}")
    print(f"Total samples: {total_samples}")

    if results:
        # Average balance across all symbols
        all_balances = []
        for symbol, df in results.items():
            label_cols = [col for col in df.columns if col.startswith('label_h')]
            engineer = LabelEngineer()
            stats = engineer.analyze_label_distribution(df, label_cols)
            for stat in stats.values():
                all_balances.append(stat['balance'])

        avg_balance = sum(all_balances) / len(all_balances) if all_balances else 0
        print(f"Average class balance: {avg_balance:.2f}")

        if avg_balance < 0.4:
            print("\nWARNING: Overall class imbalance detected. Consider:")
            print("   1. Reduce min_profit_pips from 3 to 2 or 1")
            print("   2. Collect data during more volatile market conditions")
            print("   3. Use class balancing in training pipeline")
        elif avg_balance > 0.7:
            print("\nGood class balance - ready for training!")
        else:
            print("\nAcceptable class balance")

    print("="*70 + "\n")

    return results


def save_labeled_data(results: dict, output_dir: str = "data/labeled"):
    """Save labeled data to CSV files"""
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for symbol, df in results.items():
        filename = output_path / f"{symbol.lower()}_labeled_1m.csv"
        df.to_csv(filename, index=False)
        print(f"Saved: {filename} ({len(df)} rows)")

    print(f"\nAll labeled data saved to {output_dir}/")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate labels from bar data')
    parser.add_argument('--timeframe', type=str, default='1m',
                       help='Timeframe to use (default: 1m)')
    parser.add_argument('--symbol', type=str, default=None,
                       help='Single symbol to process (default: all)')
    parser.add_argument('--save', action='store_true',
                       help='Save labeled data to CSV files')

    args = parser.parse_args()

    if args.symbol:
        # Process single symbol
        df_labeled = create_labels_for_symbol(args.symbol, args.timeframe)

        if args.save and df_labeled is not None:
            save_labeled_data({args.symbol: df_labeled})
    else:
        # Process all symbols
        results = create_labels_for_all_symbols(args.timeframe)

        if args.save and results:
            save_labeled_data(results)


if __name__ == '__main__':
    main()

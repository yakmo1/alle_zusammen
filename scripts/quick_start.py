"""
Quick Start Script
Startet das System mit minimaler Konfiguration zum Testen
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("TRADING SYSTEM UNIFIED - Quick Start")
print("=" * 70)

# Test 1: Config
print("\n[1/5] Testing Configuration...")
try:
    from src.utils.config_loader import get_config
    config = get_config()
    config.validate()
    print("    OK: Configuration valid")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

# Test 2: Database
print("\n[2/5] Testing Database Connection...")
try:
    from src.data.database_manager import get_database
    db = get_database('local')
    if db.test_connection():
        print("    OK: Database connected")
        tables = db.list_tables()
        print(f"    INFO: {len(tables)} tables found")
    else:
        print("    ERROR: Database connection failed")
        sys.exit(1)
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

# Test 3: MT5
print("\n[3/5] Testing MT5 Connection...")
try:
    import MetaTrader5 as mt5

    mt5_config = config.get_mt5_config()

    if not mt5.initialize(path=mt5_config.get('path')):
        print(f"    WARNING: MT5 not initialized - {mt5.last_error()}")
        print("    INFO: Make sure MT5 is running")
    else:
        if mt5.login(
            login=mt5_config['login'],
            password=mt5_config['password'],
            server=mt5_config['server']
        ):
            account_info = mt5.account_info()
            print(f"    OK: MT5 connected")
            print(f"    INFO: Account {account_info.login}, Balance: {account_info.balance:.2f}")
            mt5.shutdown()
        else:
            print(f"    WARNING: MT5 login failed - {mt5.last_error()}")
            mt5.shutdown()
except Exception as e:
    print(f"    ERROR: {e}")

# Test 4: Data Pipeline Components
print("\n[4/5] Testing Data Pipeline Components...")
try:
    from src.data.tick_collector import TickCollector
    from src.data.bar_builder import BarBuilder
    from src.data.feature_calculator import FeatureCalculator

    print("    OK: Tick Collector loaded")
    print("    OK: Bar Builder loaded")
    print("    OK: Feature Calculator loaded")
except Exception as e:
    print(f"    ERROR: {e}")

# Test 5: Dashboard
print("\n[5/5] Checking Dashboard Files...")
dashboard_path = Path(__file__).parent.parent / "dashboards" / "matrix_dashboard" / "unified_master_dashboard.py"
if dashboard_path.exists():
    print(f"    OK: Matrix Dashboard found")
else:
    print(f"    WARNING: Matrix Dashboard not found at {dashboard_path}")

print("\n" + "=" * 70)
print("SYSTEM STATUS: READY")
print("=" * 70)

print("\nNext Steps:")
print("1. Initialize Database:")
print("   python scripts/init_database.py --db local")
print("\n2. Start Tick Collector (30 seconds test):")
print("   python src/data/tick_collector.py")
print("\n3. Check if bars are being built:")
print("   python src/data/bar_builder.py")
print("\n4. Start full system:")
print("   python scripts/start_system.py")

print("\n" + "=" * 70)

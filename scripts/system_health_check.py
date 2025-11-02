"""
System Health Check
Überprüft alle Systemkomponenten
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, date

print("=" * 70)
print("TRADING SYSTEM - Health Check")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

health_status = {"critical": [], "warnings": [], "ok": []}

# 1. Configuration
print("\n### Configuration ###")
try:
    from src.utils.config_loader import get_config
    config = get_config()
    config.validate()
    health_status["ok"].append("Configuration")
    print("  [OK] Configuration valid")
except Exception as e:
    health_status["critical"].append("Configuration")
    print(f"  [CRITICAL] Configuration error: {e}")

# 2. Database Connection
print("\n### Database Connection ###")
try:
    from src.data.database_manager import get_database
    db = get_database('local')

    if db.test_connection():
        health_status["ok"].append("Database Connection")
        print("  [OK] Database connected")

        # Connection Info
        info = db.get_connection_info()
        print(f"  INFO: {info['host']}:{info['port']}/{info['database']}")

        # Table Count
        tables = db.list_tables()
        print(f"  INFO: {len(tables)} tables found")

        # Check critical tables
        critical_tables = ['bars_1m', 'bars_5m', 'features', 'trades']
        missing_tables = [t for t in critical_tables if t not in tables]

        if missing_tables:
            health_status["warnings"].append(f"Missing tables: {', '.join(missing_tables)}")
            print(f"  [WARNING] Missing tables: {', '.join(missing_tables)}")
            print("  ACTION: Run 'python scripts/init_database.py --db local'")

        # Check today's tick table
        today_table = f"ticks_{date.today().strftime('%Y%m%d')}"
        if today_table in tables:
            tick_count = db.get_table_row_count(today_table)
            print(f"  INFO: Today's ticks: {tick_count}")
            if tick_count == 0:
                health_status["warnings"].append("No ticks collected today")
                print("  [WARNING] No ticks collected today")
                print("  ACTION: Start Tick Collector")
        else:
            health_status["warnings"].append("Today's tick table not found")
            print(f"  [WARNING] {today_table} not found")

        # Check bars
        for timeframe in ['1m', '5m']:
            table = f'bars_{timeframe}'
            if table in tables:
                count = db.get_table_row_count(table)
                print(f"  INFO: {table}: {count} bars")

    else:
        health_status["critical"].append("Database Connection")
        print("  [CRITICAL] Database connection failed")

except Exception as e:
    health_status["critical"].append("Database")
    print(f"  [CRITICAL] Database error: {e}")

# 3. MT5 Connection
print("\n### MT5 Connection ###")
try:
    import MetaTrader5 as mt5

    mt5_config = config.get_mt5_config()

    if mt5.initialize(path=mt5_config.get('path')):
        if mt5.login(
            login=mt5_config['login'],
            password=mt5_config['password'],
            server=mt5_config['server']
        ):
            health_status["ok"].append("MT5 Connection")
            account_info = mt5.account_info()
            terminal_info = mt5.terminal_info()

            print("  [OK] MT5 connected")
            print(f"  INFO: Account: {account_info.login}")
            print(f"  INFO: Balance: {account_info.balance:.2f} {account_info.currency}")
            print(f"  INFO: Connected: {terminal_info.connected}")
            print(f"  INFO: Trade Allowed: {terminal_info.trade_allowed}")

            # Check symbols
            symbols = config.get_symbols()
            for symbol in symbols:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info and symbol_info.visible:
                    print(f"  INFO: {symbol}: Bid={symbol_info.bid:.5f}, Ask={symbol_info.ask:.5f}")
                else:
                    health_status["warnings"].append(f"Symbol {symbol} not visible")
                    print(f"  [WARNING] {symbol} not visible/available")

            mt5.shutdown()
        else:
            health_status["critical"].append("MT5 Login")
            print(f"  [CRITICAL] MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
    else:
        health_status["warnings"].append("MT5 Initialization")
        print(f"  [WARNING] MT5 not initialized: {mt5.last_error()}")
        print("  ACTION: Make sure MT5 is running")

except Exception as e:
    health_status["warnings"].append("MT5")
    print(f"  [WARNING] MT5 error: {e}")

# 4. Data Pipeline Components
print("\n### Data Pipeline Components ###")
try:
    from src.data.tick_collector import TickCollector
    health_status["ok"].append("Tick Collector Module")
    print("  [OK] Tick Collector available")
except Exception as e:
    health_status["critical"].append("Tick Collector Module")
    print(f"  [CRITICAL] Tick Collector error: {e}")

try:
    from src.data.bar_builder import BarBuilder
    health_status["ok"].append("Bar Builder Module")
    print("  [OK] Bar Builder available")
except Exception as e:
    health_status["critical"].append("Bar Builder Module")
    print(f"  [CRITICAL] Bar Builder error: {e}")

try:
    from src.data.feature_calculator import FeatureCalculator
    health_status["ok"].append("Feature Calculator Module")
    print("  [OK] Feature Calculator available")
except Exception as e:
    health_status["critical"].append("Feature Calculator Module")
    print(f"  [CRITICAL] Feature Calculator error: {e}")

# 5. Dashboard Files
print("\n### Dashboard Components ###")
dashboard_path = Path(__file__).parent.parent / "dashboards" / "matrix_dashboard" / "unified_master_dashboard.py"
if dashboard_path.exists():
    health_status["ok"].append("Matrix Dashboard")
    print(f"  [OK] Matrix Dashboard available")
    print(f"  INFO: {dashboard_path}")
else:
    health_status["warnings"].append("Matrix Dashboard")
    print(f"  [WARNING] Matrix Dashboard not found")

# 6. ML System
print("\n### ML System ###")
try:
    from src.ml.model_trainer import ModelTrainer
    from src.ml.inference_engine import InferenceEngine
    health_status["ok"].append("ML Modules")
    print("  [OK] ML modules available")

    # Check for trained models
    models_path = Path(__file__).parent.parent / "models"
    if models_path.exists():
        model_files = list(models_path.glob("*.joblib"))
        if model_files:
            health_status["ok"].append("Trained Models")
            print(f"  [OK] {len(model_files)} trained models found")
        else:
            health_status["warnings"].append("No trained models")
            print("  [WARNING] No trained models found")
            print("  ACTION: Run 'python scripts/train_models.py'")
    else:
        health_status["warnings"].append("Models directory")
        print("  [WARNING] Models directory not found")
        models_path.mkdir(exist_ok=True)
        print("  ACTION: Created models directory")

except Exception as e:
    health_status["warnings"].append("ML System")
    print(f"  [WARNING] ML System error: {e}")

# 7. Trading Engine
print("\n### Trading Engine ###")
try:
    from src.core.signal_generator import SignalGenerator
    from src.core.order_executor import OrderExecutor
    from src.core.trade_monitor import TradeMonitor
    health_status["ok"].append("Trading Engine Modules")
    print("  [OK] Trading engine modules available")
except Exception as e:
    health_status["critical"].append("Trading Engine")
    print(f"  [CRITICAL] Trading engine error: {e}")

# 8. Log Files
print("\n### Log System ###")
log_path = Path(__file__).parent.parent / "logs"
if log_path.exists():
    log_files = list(log_path.glob("*.log"))
    health_status["ok"].append("Logging")
    print(f"  [OK] Logging configured")
    print(f"  INFO: {len(log_files)} log files")
else:
    health_status["warnings"].append("Logging")
    print("  [WARNING] Logs directory not found")
    log_path.mkdir(exist_ok=True)
    print("  ACTION: Created logs directory")

# Summary
print("\n" + "=" * 70)
print("HEALTH CHECK SUMMARY")
print("=" * 70)

print(f"\n[OK] {len(health_status['ok'])} components healthy:")
for item in health_status["ok"]:
    print(f"  - {item}")

if health_status["warnings"]:
    print(f"\n[WARNING] {len(health_status['warnings'])} warnings:")
    for item in health_status["warnings"]:
        print(f"  - {item}")

if health_status["critical"]:
    print(f"\n[CRITICAL] {len(health_status['critical'])} critical issues:")
    for item in health_status["critical"]:
        print(f"  - {item}")

    print("\nACTION REQUIRED: Fix critical issues before starting system!")
    sys.exit(1)
elif health_status["warnings"]:
    print("\nSTATUS: System operational with warnings")
    print("RECOMMENDATION: Address warnings for optimal performance")
    sys.exit(0)
else:
    print("\nSTATUS: All systems healthy!")
    print("READY: System ready to start")
    sys.exit(0)

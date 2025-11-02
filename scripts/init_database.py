"""
Database Initialization Script
Erstellt alle notwendigen Tabellen und Indizes
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database_manager import get_database
from src.utils.logger import get_logger, log_exception

logger = get_logger('init_database')

# SQL Schema Definitions
SCHEMA_DEFINITIONS = {
    # Ticks Table (täglich partitioniert)
    'ticks_template': """
        CREATE TABLE IF NOT EXISTS ticks_{date} (
            id BIGSERIAL,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            bid DECIMAL(10, 5) NOT NULL,
            ask DECIMAL(10, 5) NOT NULL,
            last DECIMAL(10, 5),
            volume BIGINT,
            time_msc BIGINT,
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);

        CREATE INDEX IF NOT EXISTS idx_ticks_{date}_timestamp ON ticks_{date} (timestamp);
        CREATE INDEX IF NOT EXISTS idx_ticks_{date}_symbol ON ticks_{date} (symbol);
    """,

    # Bars Tables (verschiedene Timeframes)
    'bars_5s': """
        CREATE TABLE IF NOT EXISTS bars_5s (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            volume BIGINT DEFAULT 0,
            tick_count INTEGER DEFAULT 0,
            spread_avg DECIMAL(10, 5),
            UNIQUE(symbol, timestamp)
        );

        CREATE INDEX IF NOT EXISTS idx_bars_5s_timestamp ON bars_5s (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_bars_5s_symbol_timestamp ON bars_5s (symbol, timestamp DESC);
    """,

    'bars_1m': """
        CREATE TABLE IF NOT EXISTS bars_1m (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            volume BIGINT DEFAULT 0,
            tick_count INTEGER DEFAULT 0,
            spread_avg DECIMAL(10, 5),
            UNIQUE(symbol, timestamp)
        );

        CREATE INDEX IF NOT EXISTS idx_bars_1m_timestamp ON bars_1m (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_bars_1m_symbol_timestamp ON bars_1m (symbol, timestamp DESC);
    """,

    'bars_5m': """
        CREATE TABLE IF NOT EXISTS bars_5m (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            volume BIGINT DEFAULT 0,
            UNIQUE(symbol, timestamp)
        );

        CREATE INDEX IF NOT EXISTS idx_bars_5m_timestamp ON bars_5m (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_bars_5m_symbol_timestamp ON bars_5m (symbol, timestamp DESC);
    """,

    'bars_15m': """
        CREATE TABLE IF NOT EXISTS bars_15m (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            volume BIGINT DEFAULT 0,
            UNIQUE(symbol, timestamp)
        );

        CREATE INDEX IF NOT EXISTS idx_bars_15m_timestamp ON bars_15m (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_bars_15m_symbol_timestamp ON bars_15m (symbol, timestamp DESC);
    """,

    'bars_1h': """
        CREATE TABLE IF NOT EXISTS bars_1h (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            volume BIGINT DEFAULT 0,
            UNIQUE(symbol, timestamp)
        );

        CREATE INDEX IF NOT EXISTS idx_bars_1h_timestamp ON bars_1h (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_bars_1h_symbol_timestamp ON bars_1h (symbol, timestamp DESC);
    """,

    'bars_4h': """
        CREATE TABLE IF NOT EXISTS bars_4h (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            volume BIGINT DEFAULT 0,
            UNIQUE(symbol, timestamp)
        );

        CREATE INDEX IF NOT EXISTS idx_bars_4h_timestamp ON bars_4h (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_bars_4h_symbol_timestamp ON bars_4h (symbol, timestamp DESC);
    """,

    'bars_1d': """
        CREATE TABLE IF NOT EXISTS bars_1d (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            volume BIGINT DEFAULT 0,
            UNIQUE(symbol, timestamp)
        );

        CREATE INDEX IF NOT EXISTS idx_bars_1d_timestamp ON bars_1d (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_bars_1d_symbol_timestamp ON bars_1d (symbol, timestamp DESC);
    """,

    # Features Table
    'features': """
        CREATE TABLE IF NOT EXISTS features (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            sma_10 DECIMAL(10, 5),
            sma_20 DECIMAL(10, 5),
            sma_50 DECIMAL(10, 5),
            ema_10 DECIMAL(10, 5),
            ema_20 DECIMAL(10, 5),
            rsi_14 DECIMAL(5, 2),
            macd DECIMAL(10, 5),
            macd_signal DECIMAL(10, 5),
            macd_hist DECIMAL(10, 5),
            bb_upper DECIMAL(10, 5),
            bb_middle DECIMAL(10, 5),
            bb_lower DECIMAL(10, 5),
            atr_14 DECIMAL(10, 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp, timeframe)
        );

        CREATE INDEX IF NOT EXISTS idx_features_timestamp ON features (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_features_symbol_timeframe ON features (symbol, timeframe, timestamp DESC);
    """,

    # Model Forecasts
    'model_forecasts': """
        CREATE TABLE IF NOT EXISTS model_forecasts (
            id BIGSERIAL PRIMARY KEY,
            model_id INTEGER NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            horizon INTEGER NOT NULL,
            horizon_label VARCHAR(10) NOT NULL,
            forecast_value DECIMAL(10, 5) NOT NULL,
            confidence DECIMAL(5, 4) NOT NULL,
            signal VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_forecasts_timestamp ON model_forecasts (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_forecasts_symbol_horizon ON model_forecasts (symbol, horizon, timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_forecasts_model ON model_forecasts (model_id, timestamp DESC);
    """,

    # Model Versions
    'model_versions': """
        CREATE TABLE IF NOT EXISTS model_versions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            version VARCHAR(50) NOT NULL,
            algorithm VARCHAR(50) NOT NULL,
            horizon INTEGER NOT NULL,
            horizon_label VARCHAR(10) NOT NULL,
            r2_score DECIMAL(5, 4),
            mae DECIMAL(10, 5),
            rmse DECIMAL(10, 5),
            is_active BOOLEAN DEFAULT FALSE,
            trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_path VARCHAR(255),
            scaler_path VARCHAR(255),
            feature_names TEXT,
            UNIQUE(name, version)
        );

        CREATE INDEX IF NOT EXISTS idx_models_active ON model_versions (is_active, trained_at DESC);
        CREATE INDEX IF NOT EXISTS idx_models_horizon ON model_versions (horizon, is_active);
    """,

    # Trades Table
    'trades': """
        CREATE TABLE IF NOT EXISTS trades (
            id BIGSERIAL PRIMARY KEY,
            ticket BIGINT UNIQUE,
            symbol VARCHAR(20) NOT NULL,
            type VARCHAR(10) NOT NULL,
            volume DECIMAL(10, 2) NOT NULL,
            open_price DECIMAL(10, 5) NOT NULL,
            close_price DECIMAL(10, 5),
            sl DECIMAL(10, 5),
            tp DECIMAL(10, 5),
            profit DECIMAL(10, 2),
            commission DECIMAL(10, 2),
            swap DECIMAL(10, 2),
            open_time TIMESTAMP NOT NULL,
            close_time TIMESTAMP,
            comment TEXT,
            magic_number INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades (symbol, open_time DESC);
        CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades (open_time DESC);
        CREATE INDEX IF NOT EXISTS idx_trades_ticket ON trades (ticket);
    """,

    # Orders Table
    'orders': """
        CREATE TABLE IF NOT EXISTS orders (
            id BIGSERIAL PRIMARY KEY,
            ticket BIGINT UNIQUE,
            symbol VARCHAR(20) NOT NULL,
            type VARCHAR(10) NOT NULL,
            volume DECIMAL(10, 2) NOT NULL,
            price DECIMAL(10, 5) NOT NULL,
            sl DECIMAL(10, 5),
            tp DECIMAL(10, 5),
            status VARCHAR(20) NOT NULL,
            open_time TIMESTAMP NOT NULL,
            close_time TIMESTAMP,
            comment TEXT,
            error_code INTEGER,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status, open_time DESC);
        CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders (symbol, open_time DESC);
    """,

    # Signals Table
    'signals': """
        CREATE TABLE IF NOT EXISTS signals (
            id BIGSERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            signal_type VARCHAR(10) NOT NULL,
            confidence DECIMAL(5, 4) NOT NULL,
            horizon VARCHAR(10) NOT NULL,
            price DECIMAL(10, 5) NOT NULL,
            reason TEXT,
            executed BOOLEAN DEFAULT FALSE,
            order_id BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals (created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals (symbol, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_signals_executed ON signals (executed, created_at DESC);
    """,

    # Performance Metrics
    'performance_metrics': """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id BIGSERIAL PRIMARY KEY,
            date DATE NOT NULL,
            total_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            total_profit DECIMAL(10, 2) DEFAULT 0,
            total_loss DECIMAL(10, 2) DEFAULT 0,
            net_profit DECIMAL(10, 2) DEFAULT 0,
            win_rate DECIMAL(5, 2),
            profit_factor DECIMAL(5, 2),
            sharpe_ratio DECIMAL(5, 2),
            max_drawdown DECIMAL(10, 2),
            avg_win DECIMAL(10, 2),
            avg_loss DECIMAL(10, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date)
        );

        CREATE INDEX IF NOT EXISTS idx_metrics_date ON performance_metrics (date DESC);
    """,

    # System Logs
    'system_logs': """
        CREATE TABLE IF NOT EXISTS system_logs (
            id BIGSERIAL PRIMARY KEY,
            level VARCHAR(20) NOT NULL,
            component VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            details JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs (created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs (level, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_logs_component ON system_logs (component, created_at DESC);
    """
}


def init_database(db_type: str = 'local'):
    """
    Initialisiert die Datenbank

    Args:
        db_type: 'local' oder 'remote'
    """
    logger.info(f"Initializing database ({db_type})...")

    try:
        db = get_database(db_type)

        # Test Connection
        if not db.test_connection():
            raise ConnectionError(f"Could not connect to {db_type} database")

        logger.info(f"✓ Connected to {db_type} database")

        # Create Tables
        for table_name, schema_sql in SCHEMA_DEFINITIONS.items():
            if table_name == 'ticks_template':
                # Skip template (wird dynamisch erstellt)
                continue

            try:
                logger.info(f"Creating table: {table_name}")
                db.execute(schema_sql)
                logger.info(f"✓ Table {table_name} created/verified")
            except Exception as e:
                log_exception(logger, e, f"Failed to create table {table_name}")
                raise

        # List all tables
        logger.info("\n=== Database Tables ===")
        tables = db.list_tables()
        for table in tables:
            row_count = db.get_table_row_count(table)
            size = db.get_table_size(table)
            logger.info(f"  {table}: {row_count} rows, {size}")

        logger.info(f"\n✓ Database initialization complete ({db_type})")
        return True

    except Exception as e:
        log_exception(logger, e, f"Database initialization failed ({db_type})")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Initialize Trading System Database')
    parser.add_argument('--db', choices=['local', 'remote', 'both'], default='local',
                        help='Database to initialize (default: local)')

    args = parser.parse_args()

    print("=" * 60)
    print("Trading System - Database Initialization")
    print("=" * 60)

    if args.db in ['local', 'both']:
        print("\n### Initializing LOCAL Database ###")
        success_local = init_database('local')

    if args.db in ['remote', 'both']:
        print("\n### Initializing REMOTE Database ###")
        success_remote = init_database('remote')

    print("\n" + "=" * 60)
    if args.db == 'both':
        if success_local and success_remote:
            print("✓ Both databases initialized successfully")
        else:
            print("✗ Some databases failed to initialize")
    else:
        print("✓ Database initialization complete")
    print("=" * 60)

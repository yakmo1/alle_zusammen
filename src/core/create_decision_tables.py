#!/usr/bin/env python3
"""
Create Order Decision Tracking Table
"""

import sqlite3
from datetime import datetime

def create_decision_tracking_table():
    conn = sqlite3.connect("trading_robot.db")
    cursor = conn.cursor()
    
    # Create order_decisions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            symbol TEXT NOT NULL,
            signal_action TEXT NOT NULL,
            signal_confidence REAL NOT NULL,
            decision TEXT NOT NULL,
            decision_reasons TEXT,
            trading_conditions TEXT,
            account_info TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (signal_id) REFERENCES trading_signals (id)
        )
    """)
    
    # Create risk_settings table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            max_risk_per_trade REAL DEFAULT 2.0,
            max_daily_loss REAL DEFAULT 5.0,
            max_positions INTEGER DEFAULT 3,
            min_confidence REAL DEFAULT 0.65,
            max_correlation REAL DEFAULT 0.8,
            max_spread_points INTEGER DEFAULT 20,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default risk settings if none exist
    cursor.execute("SELECT COUNT(*) FROM risk_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO risk_settings 
            (max_risk_per_trade, max_daily_loss, max_positions, min_confidence, max_correlation, max_spread_points)
            VALUES (2.0, 5.0, 3, 0.65, 0.8, 20)
        """)
    
    conn.commit()
    conn.close()
    print("✅ Order decision tracking tables created successfully!")

if __name__ == "__main__":
    create_decision_tracking_table()

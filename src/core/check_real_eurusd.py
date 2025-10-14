#!/usr/bin/env python3
import psycopg2
from datetime import datetime

try:
    print("Connecting to trading_bot database...")
    conn = psycopg2.connect(
        host='212.132.105.198', 
        database='trading_bot', 
        user='mt5user', 
        password='1234', 
        port=5432
    )
    cursor = conn.cursor()
    
    # Check the most recent EURUSD ticks
    cursor.execute("""
        SELECT id, symbol, bid, ask, time 
        FROM ticks 
        WHERE symbol = 'EURUSD' 
        ORDER BY time DESC 
        LIMIT 20
    """)
    recent_ticks = cursor.fetchall()
    print("Most recent 20 EURUSD ticks:")
    for tick in recent_ticks:
        bid = float(tick[2])
        ask = float(tick[3])
        spread = ask - bid
        print(f"  {tick[4]}: Bid={bid:.5f}, Ask={ask:.5f}, Spread={spread*10000:.1f} pips")
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_ticks,
            MIN(bid) as min_bid,
            MAX(bid) as max_bid,
            AVG(bid) as avg_bid,
            MIN(time) as first_time,
            MAX(time) as last_time
        FROM ticks 
        WHERE symbol = 'EURUSD'
    """)
    stats = cursor.fetchone()
    print(f"\nEURUSD Statistics:")
    print(f"  Total ticks: {stats[0]}")
    print(f"  Bid range: {float(stats[1]):.5f} - {float(stats[2]):.5f}")
    print(f"  Average bid: {float(stats[3]):.5f}")
    print(f"  First record: {stats[4]}")
    print(f"  Last record: {stats[5]}")
    
    # Check what the dashboard is currently using
    print(f"\nDashboard shows: Current Price 1.04850")
    print(f"Actual latest bid: {float(recent_ticks[0][2]):.5f}")
    print(f"Difference: {float(recent_ticks[0][2]) - 1.04850:.5f}")
    
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')

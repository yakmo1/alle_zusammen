#!/usr/bin/env python3
import psycopg2
from datetime import datetime

try:
    print("Checking for daily EURUSD tables...")
    conn = psycopg2.connect(
        host='212.132.105.198', 
        database='trading_bot', 
        user='mt5user', 
        password='1234', 
        port=5432
    )
    cursor = conn.cursor()
    
    # Find all EURUSD tables with dates
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'ticks_eurusd_%'
        ORDER BY table_name DESC
    """)
    tables = cursor.fetchall()
    print(f"Found {len(tables)} daily EURUSD tables:")
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*), MIN(time), MAX(time) FROM {table_name}")
        result = cursor.fetchone()
        print(f"  {table_name}: {result[0]} ticks, {result[1]} to {result[2]}")
    
    # Check today's table specifically
    today = datetime.now().strftime('%Y%m%d')
    today_table = f"ticks_eurusd_{today}"
    print(f"\nChecking today's table: {today_table}")
    
    try:
        cursor.execute(f"""
            SELECT bid, ask, time 
            FROM {today_table} 
            WHERE bid IS NOT NULL AND ask IS NOT NULL 
            ORDER BY time DESC 
            LIMIT 5
        """)
        recent = cursor.fetchall()
        print("Most recent 5 ticks from today:")
        for tick in recent:
            bid = float(tick[0])
            ask = float(tick[1])
            spread = (ask - bid) * 10000
            print(f"  {tick[2]}: Bid={bid:.5f}, Ask={ask:.5f}, Spread={spread:.1f} pips")
            
    except Exception as e:
        print(f"Error accessing {today_table}: {e}")
    
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')

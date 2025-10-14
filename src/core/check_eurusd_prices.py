#!/usr/bin/env python3
import psycopg2
from datetime import datetime

try:
    print("Connecting to database...")
    conn = psycopg2.connect(
        host='212.132.105.198', 
        database='mt5_trading_data', 
        user='mt5user', 
        password='1234', 
        port=5432
    )
    cursor = conn.cursor()
    
    # Check all EURUSD tables
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name LIKE '%eurusd%'
        ORDER BY table_name DESC
    """)
    tables = cursor.fetchall()
    print('EURUSD Tables found:', [t[0] for t in tables])
    
    if tables:
        table_name = tables[0][0]
        print(f'\nChecking latest data in: {table_name}')
        cursor.execute(f'SELECT MAX(time), AVG(bid), AVG(ask), COUNT(*) FROM {table_name} WHERE bid IS NOT NULL')
        result = cursor.fetchone()
        print(f'Latest time: {result[0]}')
        print(f'Average bid: {result[1]:.5f}')
        print(f'Average ask: {result[2]:.5f}')
        print(f'Total records: {result[3]}')
        
        # Check recent data with better range
        cursor.execute(f"""
            SELECT bid, ask, time FROM {table_name} 
            WHERE bid IS NOT NULL AND bid > 1.10 AND bid < 1.20
            ORDER BY time DESC 
            LIMIT 10
        """)
        recent = cursor.fetchall()
        print('\nMost recent 10 realistic records (1.10-1.20 range):')
        for r in recent:
            print(f'  {r[2]}: Bid={r[0]:.5f}, Ask={r[1]:.5f}')
            
        # Check what data range we actually have
        cursor.execute(f'SELECT MIN(bid), MAX(bid), COUNT(*) FROM {table_name} WHERE bid IS NOT NULL')
        range_result = cursor.fetchone()
        print(f'\nData range: Min={range_result[0]:.5f}, Max={range_result[1]:.5f}, Count={range_result[2]}')
    
    conn.close()
    print("\nDatabase check complete.")
    
except Exception as e:
    print(f'Error: {e}')

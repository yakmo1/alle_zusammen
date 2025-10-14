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
    
    # Check all tables
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    print('All tables found:', [t[0] for t in tables])
    
    # Look for EURUSD related tables
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name LIKE '%eur%'
        ORDER BY table_name DESC
    """)
    eur_tables = cursor.fetchall()
    print('EURUSD/EUR related tables:', [t[0] for t in eur_tables])
    
    # Check what's in each table
    for table in tables:
        table_name = table[0]
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f'\nTable {table_name}: {count} records')
        
        if count > 0:
            # Check columns
            cursor.execute(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            print(f'  Columns: {[c[0] for c in columns]}')
            
            # Show sample data
            cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
            sample = cursor.fetchall()
            print(f'  Sample data:')
            for row in sample:
                print(f'    {row}')
    
    conn.close()
    print("\nDatabase inspection complete.")
    
except Exception as e:
    print(f'Error: {e}')

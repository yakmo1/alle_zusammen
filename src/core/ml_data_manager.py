#!/usr/bin/env python3
"""
ML Training Data Preparation for EURUSD
Sammelt alle verfügbaren EURUSD Daten für Machine Learning Training
"""

import psycopg2
from datetime import datetime, timedelta

def get_all_eurusd_training_data():
    """
    Sammelt alle EURUSD Daten aus allen verfügbaren Tabellen für ML-Training
    """
    try:
        conn = psycopg2.connect(
            host='212.132.105.198', 
            database='trading_bot', 
            user='mt5user', 
            password='1234', 
            port=5432
        )
        cursor = conn.cursor()
        
        print("=== EURUSD ML Training Data Collection ===")
        
        # Find all EURUSD tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name LIKE 'ticks_eurusd_%' OR table_name = 'ticks')
            ORDER BY table_name
        """)
        all_tables = cursor.fetchall()
        
        training_data = []
        total_records = 0
        
        for table in all_tables:
            table_name = table[0]
            print(f"\nProcessing table: {table_name}")
            
            try:
                if table_name == 'ticks':
                    # Filter for EURUSD only
                    cursor.execute(f"""
                        SELECT bid, ask, time 
                        FROM {table_name} 
                        WHERE symbol = 'EURUSD' AND bid IS NOT NULL AND ask IS NOT NULL
                        ORDER BY time ASC
                    """)
                else:
                    # Daily table - all data is EURUSD
                    cursor.execute(f"""
                        SELECT bid, ask, time 
                        FROM {table_name} 
                        WHERE bid IS NOT NULL AND ask IS NOT NULL
                        ORDER BY time ASC
                    """)
                
                table_data = cursor.fetchall()
                if table_data:
                    training_data.extend(table_data)
                    total_records += len(table_data)
                    print(f"  Added {len(table_data)} records")
                    print(f"  Date range: {table_data[0][2]} to {table_data[-1][2]}")
                else:
                    print(f"  No data found")
                    
            except Exception as e:
                print(f"  Error processing {table_name}: {e}")
        
        # Sort all data by time
        training_data.sort(key=lambda x: x[2])
        
        print(f"\n=== Training Data Summary ===")
        print(f"Total records: {total_records}")
        if training_data:
            print(f"Date range: {training_data[0][2]} to {training_data[-1][2]}")
            print(f"Price range: {min(float(t[0]) for t in training_data):.5f} to {max(float(t[0]) for t in training_data):.5f}")
        
        conn.close()
        return training_data
        
    except Exception as e:
        print(f"Error collecting training data: {e}")
        return []

def get_current_prediction_data():
    """
    Holt nur die aktuellsten Daten für Live Predictions
    """
    try:
        conn = psycopg2.connect(
            host='212.132.105.198', 
            database='trading_bot', 
            user='mt5user', 
            password='1234', 
            port=5432
        )
        cursor = conn.cursor()
        
        print("=== Current Prediction Data ===")
        
        # Try today's table first
        today = datetime.now().strftime('%Y%m%d')
        today_table = f"ticks_eurusd_{today}"
        
        current_data = None
        source_table = None
        
        try:
            cursor.execute(f"""
                SELECT bid, ask, time 
                FROM {today_table} 
                WHERE bid IS NOT NULL AND ask IS NOT NULL 
                ORDER BY time DESC 
                LIMIT 50
            """)
            current_data = cursor.fetchall()
            if current_data:
                source_table = today_table
                print(f"Using today's table: {today_table} ({len(current_data)} recent ticks)")
        except:
            print(f"Today's table {today_table} not available")
        
        # Fallback to general ticks table
        if not current_data:
            try:
                cursor.execute("""
                    SELECT bid, ask, time 
                    FROM ticks 
                    WHERE symbol = 'EURUSD' AND bid IS NOT NULL AND ask IS NOT NULL 
                    ORDER BY time DESC 
                    LIMIT 50
                """)
                current_data = cursor.fetchall()
                if current_data:
                    source_table = 'ticks'
                    print(f"Using fallback ticks table ({len(current_data)} recent EURUSD ticks)")
            except Exception as e:
                print(f"Error accessing ticks table: {e}")
        
        if current_data:
            latest = current_data[0]
            current_price = (float(latest[0]) + float(latest[1])) / 2
            print(f"Latest price: {current_price:.5f} from {latest[2]}")
            print(f"Data source: {source_table}")
        
        conn.close()
        return current_data, source_table
        
    except Exception as e:
        print(f"Error getting current data: {e}")
        return None, None

if __name__ == "__main__":
    print("EURUSD Data Analysis for ML Training and Live Trading")
    print("=" * 60)
    
    # Collect training data
    training_data = get_all_eurusd_training_data()
    
    # Get current prediction data
    current_data, source = get_current_prediction_data()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"- Training records available: {len(training_data)}")
    print(f"- Current data source: {source}")
    print(f"- Ready for ML training: {'YES' if len(training_data) > 100 else 'NO (need more data)'}")
    print(f"- Ready for live trading: {'YES' if current_data else 'NO'}")

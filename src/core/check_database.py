#!/usr/bin/env python3
import psycopg2

try:
    print("Connecting to PostgreSQL server to list databases...")
    # Connect to default postgres database first
    conn = psycopg2.connect(
        host='212.132.105.198', 
        database='postgres', 
        user='mt5user', 
        password='1234', 
        port=5432
    )
    cursor = conn.cursor()
    
    # List all databases
    cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
    databases = cursor.fetchall()
    print("Available databases:")
    for db in databases:
        print(f"  - {db[0]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error connecting to postgres: {e}")
    print("\nTrying template1 database instead...")
    
    try:
        conn = psycopg2.connect(
            host='212.132.105.198', 
            database='template1', 
            user='mt5user', 
            password='1234', 
            port=5432
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        databases = cursor.fetchall()
        print("Available databases:")
        for db in databases:
            print(f"  - {db[0]}")
        
        conn.close()
        
    except Exception as e2:
        print(f"Error with template1: {e2}")
        
        # Try different user/password combinations
        print("\nTrying alternative credentials...")
        try:
            conn = psycopg2.connect(
                host='212.132.105.198', 
                database='mt5data',  # Try different database name
                user='postgres',     # Try different user
                password='password', # Try different password
                port=5432
            )
            cursor = conn.cursor()
            cursor.execute("SELECT current_database(), current_user;")
            result = cursor.fetchone()
            print(f"Connected successfully! Database: {result[0]}, User: {result[1]}")
            conn.close()
        except Exception as e3:
            print(f"Alternative connection failed: {e3}")

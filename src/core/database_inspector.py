#!/usr/bin/env python3
"""
Database Structure Inspector - Prüft alle vorhandenen Tabellen
"""

import sqlite3
import os

def inspect_database():
    db_path = "trading_robot.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Datenbankdatei {db_path} nicht gefunden!")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("📊 Gefundene Tabellen:")
        print("=" * 50)
        
        for table in tables:
            table_name = table[0]
            print(f"\n🔍 Tabelle: {table_name}")
            
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("  Spalten:")
            for col in columns:
                print(f"    - {col[1]} ({col[2]})")
                
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  Anzahl Datensätze: {count}")
            
            # Show sample data if available
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                samples = cursor.fetchall()
                print("  Beispieldaten:")
                for sample in samples:
                    print(f"    {sample}")
                    
        conn.close()
        
    except Exception as e:
        print(f"❌ Fehler beim Lesen der Datenbank: {e}")

if __name__ == "__main__":
    inspect_database()

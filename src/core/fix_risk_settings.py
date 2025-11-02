#!/usr/bin/env python3
"""
Fix Risk Settings - Korrigiert die Min-Confidence von 70.0 auf 0.65
"""

import sqlite3

def fix_risk_settings():
    """Korrigiert die Risk Settings"""
    conn = sqlite3.connect("trading_robot.db")
    cursor = conn.cursor()
    
    # Update existing risk settings
    cursor.execute("""
        UPDATE risk_settings 
        SET min_confidence = 0.65 
        WHERE min_confidence = 70.0
    """)
    
    # Verify the change
    cursor.execute("SELECT * FROM risk_settings ORDER BY timestamp DESC LIMIT 1")
    result = cursor.fetchone()
    
    if result:
        print("✅ Risk Settings erfolgreich aktualisiert:")
        print(f"   Min Confidence: {result[4]} (sollte 0.65 sein)")
    else:
        print("❌ Keine Risk Settings gefunden")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_risk_settings()

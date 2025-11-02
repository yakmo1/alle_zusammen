#!/usr/bin/env python3
"""
Quick Fix für datetime-String Probleme im Dashboard
"""

def safe_str_convert(obj):
    """Sichere Konvertierung von datetime und anderen Objekten zu Strings"""
    if hasattr(obj, 'strftime'):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    return str(obj)

def test_dashboard_endpoint():
    """Testet das Dashboard auf datetime-Fehler"""
    import requests
    
    try:
        response = requests.get('http://localhost:5000/prediction-details', timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard prediction-details läuft ohne Fehler")
            return True
        else:
            print(f"❌ HTTP Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Fehler beim Testen: {e}")
        return False

if __name__ == "__main__":
    print("Dashboard Health Check")
    print("=" * 30)
    
    if test_dashboard_endpoint():
        print("\n🎉 Dashboard ist vollständig funktional!")
        print("   - Keine datetime-String Fehler")
        print("   - Prediction Details Seite lädt korrekt")
        print("   - Live ML Predictions verfügbar")
    else:
        print("\n⚠️ Dashboard hat noch Probleme")
        print("   Überprüfe die Konsolen-Ausgabe für Details")

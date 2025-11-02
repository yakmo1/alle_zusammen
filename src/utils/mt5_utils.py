"""
mt5_utils.py
Hilfsfunktionen für MetaTrader5-Kommunikation und Live-Datenabfrage
"""
import MetaTrader5 as mt5
import os
from dotenv import load_dotenv
import time

# Initialisierung: robust, wie getestet

def initialize_mt5():
    load_dotenv('.env', override=True)
    mt5_path = os.getenv('MT5_PATH')
    # Erst ohne Pfad, dann mit Pfad falls nötig
    if mt5.initialize():
        return True
    elif mt5_path and mt5.initialize(mt5_path):
        return True
    else:
        err = mt5.last_error() if hasattr(mt5, 'last_error') else 'Unbekannt'
        print(f"❌ MT5 konnte nicht initialisiert werden! Fehler: {err}")
        return False

def get_live_ticks(symbol: str, n: int = 10, delay: float = 1.0):
    """Gibt n Live-Ticks für das angegebene Symbol aus."""
    ticks = []
    for i in range(1, n+1):
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            ticks.append({
                'nr': i,
                'time': tick.time,
                'bid': tick.bid,
                'ask': tick.ask,
                'last': tick.last
            })
            print(f"Tick {i}: Zeit={tick.time}, Bid={tick.bid}, Ask={tick.ask}, Last={tick.last}")
        else:
            print(f"Tick {i}: Keine Tick-Daten erhalten!")
        time.sleep(delay)
    return ticks

def shutdown_mt5():
    if hasattr(mt5, 'shutdown'):
        mt5.shutdown()

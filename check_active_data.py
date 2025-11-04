#!/usr/bin/env python3
"""
CHECK ACTIVE DATA - Prüft die AKTIVE Datenbank auf dem Remote-Server

Verbindet sich zur RICHTIGEN Datenbank:
  Host: 212.132.105.198
  Database: trading_db (NICHT postgres!)
  Tabellen: bars_eurusd, bars_gbpusd, etc.
"""

import psycopg2
from datetime import datetime, timezone

# Datenbank-Verbindung zur AKTIVEN Datenbank
DB_CONFIG = {
    'host': '212.132.105.198',
    'port': 5432,
    'database': 'trading_db',  # WICHTIG: Nicht "postgres"!
    'user': 'mt5user',
    'password': '1234'
}

SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']

def check_active_database():
    """Prüft die aktive Datenbank auf neue Daten"""

    print("=" * 80)
    print("AKTIVE DATENBANK STATUS CHECK")
    print("=" * 80)
    print(f"Host:     {DB_CONFIG['host']}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"User:     {DB_CONFIG['user']}")
    print("=" * 80)
    print()

    try:
        # Verbindung herstellen
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        print("[OK] Verbindung erfolgreich!\n")

        # Prüfe jedes Symbol
        total_bars = 0
        total_recent = 0
        latest_overall = None

        print("=" * 80)
        print("DATEN PRO SYMBOL (1m Timeframe)")
        print("=" * 80)
        print(f"{'Symbol':<10} {'Total Bars':<12} {'Letzte 1h':<12} {'Neuester Bar':<25}")
        print("-" * 80)

        for symbol in SYMBOLS:
            table_name = f"bars_{symbol.lower()}"

            # Total Bars
            cur.execute(f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE timeframe = '1m'
            """)
            count = cur.fetchone()[0]
            total_bars += count

            # Bars letzte Stunde
            cur.execute(f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE timeframe = '1m'
                AND timestamp >= NOW() - INTERVAL '1 hour'
            """)
            recent = cur.fetchone()[0]
            total_recent += recent

            # Neuester Bar
            cur.execute(f"""
                SELECT MAX(timestamp) FROM {table_name}
                WHERE timeframe = '1m'
            """)
            latest = cur.fetchone()[0]

            if latest and (latest_overall is None or latest > latest_overall):
                latest_overall = latest

            print(f"{symbol:<10} {count:>11,} {recent:>11} {str(latest) if latest else 'N/A':<25}")

        print("-" * 80)
        print(f"{'GESAMT':<10} {total_bars:>11,} {total_recent:>11}")
        print("=" * 80)
        print()

        # Zeit-Analyse
        if latest_overall:
            now = datetime.now(timezone.utc)
            if not latest_overall.tzinfo:
                latest_overall = latest_overall.replace(tzinfo=timezone.utc)

            time_diff = now - latest_overall
            minutes_ago = time_diff.total_seconds() / 60

            print("=" * 80)
            print("DATENSAMMLUNG STATUS")
            print("=" * 80)
            print(f"Aktuell (UTC):       {now}")
            print(f"Neuester Bar:        {latest_overall}")
            print(f"Alter:               {minutes_ago:.1f} Minuten")
            print()

            if minutes_ago < 3:
                print("STATUS: [AKTIV] Daten werden LIVE gesammelt!")
                print("        System laeuft perfekt!")
                status = "ACTIVE"
            elif minutes_ago < 10:
                print(f"STATUS: [OK] Datensammlung aktiv (vor {minutes_ago:.1f} min)")
                status = "OK"
            elif minutes_ago < 60:
                print(f"STATUS: [WARNUNG] Verzoegerung ({minutes_ago:.0f} Minuten)")
                status = "DELAYED"
            else:
                hours = minutes_ago / 60
                print(f"STATUS: [FEHLER] Gestoppt (vor {hours:.1f} Stunden)")
                status = "STOPPED"

            print("=" * 80)
            print()

        # Wachstumsrate
        if total_recent > 0:
            print("=" * 80)
            print("WACHSTUMSRATE")
            print("=" * 80)
            bars_per_minute = total_recent / 60
            bars_per_symbol = total_recent / len(SYMBOLS)
            print(f"Bars/Minute (alle):  {bars_per_minute:.2f}")
            print(f"Bars/Stunde (alle):  {total_recent}")
            print(f"Bars/Symbol/Stunde:  {bars_per_symbol:.1f}")
            print(f"Erwartung/Symbol:    ~60 Bars/Stunde")
            print()

            if bars_per_symbol >= 50:
                print("QUALITAET: [EXCELLENT] Vollstaendige Datensammlung")
            elif bars_per_symbol >= 30:
                print("QUALITAET: [GOOD] Datensammlung laeuft gut")
            elif bars_per_symbol >= 10:
                print("QUALITAET: [WARNING] Lueckenhafte Datensammlung")
            else:
                print("QUALITAET: [POOR] Sehr lueckenhaft")

            print("=" * 80)
            print()

        # Letzte Bars von EURUSD
        print("=" * 80)
        print("LETZTE 10 BARS - EURUSD (1m)")
        print("=" * 80)
        cur.execute("""
            SELECT timestamp, open, high, low, close, volume,
                   rsi14, macd_main, atr14
            FROM bars_eurusd
            WHERE timeframe = '1m'
            ORDER BY timestamp DESC
            LIMIT 10
        """)

        print(f"{'Timestamp':<20} {'Close':<10} {'RSI14':<8} {'MACD':<10} {'ATR14':<10}")
        print("-" * 80)

        for row in cur.fetchall():
            timestamp, open_p, high, low, close, volume, rsi, macd, atr = row
            rsi_str = f"{rsi:.2f}" if rsi else "N/A"
            macd_str = f"{macd:.5f}" if macd else "N/A"
            atr_str = f"{atr:.5f}" if atr else "N/A"
            print(f"{str(timestamp):<20} {close:<10.5f} {rsi_str:<8} {macd_str:<10} {atr_str:<10}")

        print("=" * 80)
        print()

        # Zusammenfassung
        print("=" * 80)
        print("ZUSAMMENFASSUNG")
        print("=" * 80)
        if status == "ACTIVE":
            print("[SUCCESS] Datensammlung laeuft AKTIV!")
            print("          Watchdog-System funktioniert perfekt!")
            print("          ML-Training kann mit aktuellen Daten starten!")
        elif status == "OK":
            print("[OK] System laeuft, kleine Verzoegerungen normal")
        elif status == "DELAYED":
            print("[WARNING] Verzoegerung erkannt")
            print("          Pruefe Watchdog/Services auf dem Server")
        else:
            print("[ERROR] System gestoppt")
            print("        Watchdog muss Services neu starten")
        print("=" * 80)

        cur.close()
        conn.close()

    except psycopg2.OperationalError as e:
        print(f"[FEHLER] Verbindung fehlgeschlagen: {e}")
        print()
        print("MOEGLICHE URSACHEN:")
        print("1. Remote-Zugriff auf 'trading_db' nicht erlaubt")
        print("2. Firewall blockiert Zugriff")
        print("3. PostgreSQL pg_hba.conf muss angepasst werden")
        print()
        print("LOESUNG:")
        print("Auf dem Server folgende Schritte:")
        print()
        print("1. PostgreSQL Config anpassen:")
        print("   sudo nano /etc/postgresql/*/main/postgresql.conf")
        print("   Aendern: listen_addresses = '*'")
        print()
        print("2. Zugriff erlauben:")
        print("   sudo nano /etc/postgresql/*/main/pg_hba.conf")
        print("   Hinzufuegen: host  trading_db  mt5user  0.0.0.0/0  md5")
        print()
        print("3. PostgreSQL neu starten:")
        print("   sudo systemctl restart postgresql")
        print()
        print("4. Firewall-Regel (falls noetig):")
        print("   sudo ufw allow 5432/tcp")

    except Exception as e:
        print(f"[FEHLER] Unerwarteter Fehler: {e}")

if __name__ == "__main__":
    check_active_database()

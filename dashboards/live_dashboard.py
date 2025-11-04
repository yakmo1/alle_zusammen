"""
LIVE TRADING DASHBOARD
Zeigt aktuelle Live-Daten von der Remote-Datenbank (trading_db)
"""

import streamlit as st
import psycopg2
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
import time

# Seitenkonfiguration
st.set_page_config(
    page_title="Live Trading Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Matrix-Style CSS
st.markdown("""
<style>
    @keyframes matrix {
        0% { background-position: 0 0; }
        100% { background-position: 0 100vh; }
    }

    .stApp {
        background: linear-gradient(to bottom, #000000 0%, #001a00 100%) !important;
        background-image:
            repeating-linear-gradient(
                0deg,
                transparent,
                transparent 2px,
                rgba(0, 255, 65, 0.03) 2px,
                rgba(0, 255, 65, 0.03) 4px
            ) !important;
        animation: matrix 20s linear infinite;
    }

    h1, h2, h3 {
        color: #00ff41 !important;
        text-shadow: 0 0 10px #00ff41;
        font-family: 'Courier New', monospace;
    }

    .stMetric {
        background-color: rgba(0, 20, 0, 0.8) !important;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #00ff41;
    }

    .stMetric label {
        color: #00ff41 !important;
    }

    .stMetric .css-1wivap2 {
        color: #00ff41 !important;
    }
</style>
""", unsafe_allow_html=True)

# Datenbank-Konfiguration
DB_CONFIG = {
    'host': '212.132.105.198',
    'port': 5432,
    'database': 'trading_db',
    'user': 'mt5user',
    'password': '1234'
}

SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']

@st.cache_resource
def get_db_connection():
    """Erstellt Datenbankverbindung"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"Datenbankverbindung fehlgeschlagen: {e}")
        return None

def fetch_latest_bars(symbol, limit=100):
    """Holt neueste Bars für ein Symbol"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        table_name = f"bars_{symbol.lower()}"
        query = f"""
            SELECT timestamp, open, high, low, close, volume,
                   rsi14, macd_main, bb_upper, bb_lower, atr14
            FROM {table_name}
            WHERE timeframe = '1m'
            ORDER BY timestamp DESC
            LIMIT %s
        """

        df = pd.read_sql(query, conn, params=(limit,))
        df = df.sort_values('timestamp')
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten für {symbol}: {e}")
        return None

def fetch_stats(symbol):
    """Holt Statistiken für ein Symbol"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        table_name = f"bars_{symbol.lower()}"
        query = f"""
            SELECT
                COUNT(*) as total_bars,
                MAX(timestamp) as latest_bar,
                (SELECT COUNT(*) FROM {table_name}
                 WHERE timeframe='1m' AND timestamp >= NOW() - INTERVAL '1 hour') as bars_1h,
                (SELECT COUNT(*) FROM {table_name}
                 WHERE timeframe='1m' AND timestamp >= NOW() - INTERVAL '24 hours') as bars_24h
            FROM {table_name}
            WHERE timeframe = '1m'
        """

        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchone()
        cur.close()

        return {
            'total_bars': result[0],
            'latest_bar': result[1],
            'bars_1h': result[2],
            'bars_24h': result[3]
        }
    except Exception as e:
        st.error(f"Fehler beim Laden der Statistiken für {symbol}: {e}")
        return None

def render_candlestick_chart(df, symbol):
    """Rendert Candlestick Chart"""
    if df is None or df.empty:
        st.warning(f"Keine Daten für {symbol}")
        return

    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol
    )])

    # Bollinger Bands hinzufügen
    if 'bb_upper' in df.columns and df['bb_upper'].notna().any():
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['bb_upper'],
            name='BB Upper',
            line=dict(color='rgba(0, 255, 65, 0.3)', width=1)
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['bb_lower'],
            name='BB Lower',
            line=dict(color='rgba(0, 255, 65, 0.3)', width=1),
            fill='tonexty'
        ))

    fig.update_layout(
        title=f"{symbol} - 1m Chart (letzte {len(df)} Bars)",
        yaxis_title="Preis",
        xaxis_title="Zeit",
        height=500,
        template='plotly_dark',
        paper_bgcolor='rgba(0, 20, 0, 0.8)',
        plot_bgcolor='rgba(0, 0, 0, 0.8)',
        font=dict(color='#00ff41')
    )

    st.plotly_chart(fig, use_container_width=True)

def render_indicators(df):
    """Rendert Indikator-Charts"""
    if df is None or df.empty:
        return

    col1, col2 = st.columns(2)

    with col1:
        # RSI Chart
        if 'rsi14' in df.columns and df['rsi14'].notna().any():
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['rsi14'],
                name='RSI 14',
                line=dict(color='#00ff41')
            ))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")

            fig_rsi.update_layout(
                title="RSI 14",
                height=250,
                template='plotly_dark',
                paper_bgcolor='rgba(0, 20, 0, 0.8)',
                plot_bgcolor='rgba(0, 0, 0, 0.8)',
                font=dict(color='#00ff41'),
                showlegend=False
            )
            st.plotly_chart(fig_rsi, use_container_width=True)

    with col2:
        # MACD Chart
        if 'macd_main' in df.columns and df['macd_main'].notna().any():
            fig_macd = go.Figure()
            fig_macd.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['macd_main'],
                name='MACD',
                line=dict(color='#00ff41')
            ))
            fig_macd.add_hline(y=0, line_dash="dash", line_color="white")

            fig_macd.update_layout(
                title="MACD",
                height=250,
                template='plotly_dark',
                paper_bgcolor='rgba(0, 20, 0, 0.8)',
                plot_bgcolor='rgba(0, 0, 0, 0.8)',
                font=dict(color='#00ff41'),
                showlegend=False
            )
            st.plotly_chart(fig_macd, use_container_width=True)

def main():
    """Haupt-Dashboard"""

    st.title("📊 Live Trading Dashboard")
    st.markdown("**Remote Server:** 212.132.105.198 | **Database:** trading_db")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Einstellungen")

        selected_symbol = st.selectbox(
            "Symbol wählen:",
            SYMBOLS,
            index=0
        )

        bars_to_show = st.slider(
            "Bars anzeigen:",
            min_value=20,
            max_value=500,
            value=100,
            step=10
        )

        auto_refresh = st.checkbox("Auto-Refresh (60s)", value=True)

        if st.button("🔄 Jetzt aktualisieren"):
            st.rerun()

    # Hole Statistiken für alle Symbole
    st.subheader("📈 System-Übersicht")

    cols = st.columns(len(SYMBOLS))
    total_bars_all = 0
    total_1h_all = 0

    for i, symbol in enumerate(SYMBOLS):
        stats = fetch_stats(symbol)
        if stats:
            total_bars_all += stats['total_bars']
            total_1h_all += stats['bars_1h']

            with cols[i]:
                # Zeit seit letztem Bar
                if stats['latest_bar']:
                    now = datetime.now(timezone.utc)
                    latest = stats['latest_bar']
                    if not latest.tzinfo:
                        latest = latest.replace(tzinfo=timezone.utc)

                    age_minutes = (now - latest).total_seconds() / 60

                    if age_minutes < 5:
                        status = "🟢"
                    elif age_minutes < 15:
                        status = "🟡"
                    else:
                        status = "🔴"

                    st.metric(
                        label=f"{status} {symbol}",
                        value=f"{stats['bars_1h']} Bars/h",
                        delta=f"{age_minutes:.1f} min ago"
                    )
                else:
                    st.metric(label=symbol, value="N/A")

    # Gesamtstatistik
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Bars", f"{total_bars_all:,}")

    with col2:
        st.metric("Bars/Stunde (alle)", f"{total_1h_all}")

    with col3:
        rate = total_1h_all / 60 if total_1h_all > 0 else 0
        st.metric("Bars/Minute", f"{rate:.1f}")

    with col4:
        quality = "EXCELLENT" if total_1h_all > 250 else "GOOD" if total_1h_all > 100 else "LOW"
        st.metric("Qualität", quality)

    st.markdown("---")

    # Hauptchart für gewähltes Symbol
    st.subheader(f"📊 {selected_symbol} Live Chart")

    df = fetch_latest_bars(selected_symbol, bars_to_show)

    if df is not None and not df.empty:
        # Candlestick Chart
        render_candlestick_chart(df, selected_symbol)

        # Indikatoren
        st.subheader("📉 Technische Indikatoren")
        render_indicators(df)

        # Letzte Bars Tabelle
        with st.expander("📋 Letzte 10 Bars (Details)"):
            latest_10 = df.tail(10)[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'rsi14', 'macd_main', 'atr14']]
            latest_10 = latest_10.sort_values('timestamp', ascending=False)
            st.dataframe(latest_10, use_container_width=True)

    else:
        st.error(f"Keine Daten für {selected_symbol} verfügbar!")

    # Auto-Refresh
    if auto_refresh:
        time.sleep(60)
        st.rerun()

if __name__ == "__main__":
    main()

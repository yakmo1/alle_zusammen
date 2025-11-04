#!/bin/bash
################################################################################
# REMOTE SERVER SETUP SCRIPT
# Automatisierte Einrichtung der Datensammlung auf 212.132.105.198
################################################################################

set -e  # Stop on errors

echo "=========================================="
echo "🚀 REMOTE SERVER SETUP GESTARTET"
echo "=========================================="
echo ""

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variablen
PROJECT_DIR="/opt/alle_zusammen"
VENV_DIR="$PROJECT_DIR/venv"
REPO_URL="https://github.com/yakmo1/alle_zusammen.git"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="mt5user"
DB_PASS="1234"

################################################################################
# TASK 1: System-Voraussetzungen prüfen
################################################################################

echo -e "${YELLOW}[TASK 1/10]${NC} System-Voraussetzungen prüfen..."

# Python Version prüfen
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} Python gefunden: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python3 nicht gefunden!"
    echo "Installiere Python3:"
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Git prüfen
if command -v git &> /dev/null; then
    echo -e "${GREEN}✓${NC} Git gefunden: $(git --version)"
else
    echo -e "${RED}✗${NC} Git nicht gefunden!"
    echo "Installiere Git:"
    sudo apt install -y git
fi

# PostgreSQL prüfen
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✓${NC} PostgreSQL gefunden: $(psql --version)"
else
    echo -e "${YELLOW}⚠${NC} PostgreSQL Client nicht gefunden, installiere..."
    sudo apt install -y postgresql-client
fi

echo ""

################################################################################
# TASK 2: Alte Prozesse stoppen
################################################################################

echo -e "${YELLOW}[TASK 2/10]${NC} Alte Prozesse stoppen..."

# Suche nach laufenden Python-Prozessen
TICK_PIDS=$(pgrep -f "start_tick_collector" || true)
BAR_PIDS=$(pgrep -f "start_bar_aggregator" || true)
FEATURE_PIDS=$(pgrep -f "start_feature" || true)

if [ ! -z "$TICK_PIDS" ]; then
    echo "Stoppe Tick Collector (PIDs: $TICK_PIDS)..."
    kill $TICK_PIDS 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✓${NC} Tick Collector gestoppt"
else
    echo -e "${YELLOW}ℹ${NC} Kein Tick Collector läuft"
fi

if [ ! -z "$BAR_PIDS" ]; then
    echo "Stoppe Bar Aggregator (PIDs: $BAR_PIDS)..."
    kill $BAR_PIDS 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✓${NC} Bar Aggregator gestoppt"
else
    echo -e "${YELLOW}ℹ${NC} Kein Bar Aggregator läuft"
fi

if [ ! -z "$FEATURE_PIDS" ]; then
    echo "Stoppe Feature Calculator (PIDs: $FEATURE_PIDS)..."
    kill $FEATURE_PIDS 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✓${NC} Feature Calculator gestoppt"
else
    echo -e "${YELLOW}ℹ${NC} Kein Feature Calculator läuft"
fi

echo ""

################################################################################
# TASK 3: Projekt-Verzeichnis vorbereiten
################################################################################

echo -e "${YELLOW}[TASK 3/10]${NC} Projekt-Verzeichnis vorbereiten..."

if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}ℹ${NC} Projekt-Verzeichnis existiert bereits: $PROJECT_DIR"
    cd "$PROJECT_DIR"

    # Prüfe ob es ein Git-Repo ist
    if [ -d ".git" ]; then
        echo "Git-Repository gefunden, führe Pull aus..."
        git fetch origin
        git reset --hard origin/master
        echo -e "${GREEN}✓${NC} Repository aktualisiert"
    else
        echo -e "${RED}✗${NC} Kein Git-Repository! Lösche und clone neu..."
        cd ..
        sudo rm -rf "$PROJECT_DIR"
        sudo git clone "$REPO_URL" "$PROJECT_DIR"
        echo -e "${GREEN}✓${NC} Repository geklont"
    fi
else
    echo "Erstelle Projekt-Verzeichnis: $PROJECT_DIR"
    sudo mkdir -p "$PROJECT_DIR"
    sudo git clone "$REPO_URL" "$PROJECT_DIR"
    echo -e "${GREEN}✓${NC} Projekt geklont"
fi

# Berechtigungen setzen
sudo chown -R $USER:$USER "$PROJECT_DIR"

echo ""

################################################################################
# TASK 4: Virtual Environment erstellen
################################################################################

echo -e "${YELLOW}[TASK 4/10]${NC} Virtual Environment erstellen..."

cd "$PROJECT_DIR"

if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}ℹ${NC} Virtual Environment existiert bereits"
    echo "Lösche altes venv und erstelle neu..."
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
echo -e "${GREEN}✓${NC} Virtual Environment erstellt"

# Aktiviere venv
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓${NC} Virtual Environment aktiviert"

echo ""

################################################################################
# TASK 5: Dependencies installieren
################################################################################

echo -e "${YELLOW}[TASK 5/10]${NC} Python Dependencies installieren..."

# Upgrade pip
pip install --upgrade pip

# Prüfe ob requirements.txt existiert
if [ -f "requirements.txt" ]; then
    echo "Installiere aus requirements.txt..."
    pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies aus requirements.txt installiert"
else
    echo -e "${YELLOW}⚠${NC} requirements.txt nicht gefunden, installiere manuell..."

    # Core dependencies
    pip install psycopg2-binary pandas numpy MetaTrader5 \
                scikit-learn xgboost lightgbm imbalanced-learn \
                flask flask-socketio python-dotenv pytz

    echo -e "${GREEN}✓${NC} Core Dependencies installiert"
fi

echo ""

################################################################################
# TASK 6: Konfiguration anpassen
################################################################################

echo -e "${YELLOW}[TASK 6/10]${NC} Konfiguration für Server anpassen..."

# Config-Datei anpassen
CONFIG_FILE="config/config.json"

if [ -f "$CONFIG_FILE" ]; then
    echo "Passe $CONFIG_FILE an..."

    # Backup erstellen
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"

    # Database-Config für Server (localhost statt remote)
    python3 << 'EOF'
import json

config_file = "config/config.json"

with open(config_file, 'r') as f:
    config = json.load(f)

# Setze database active auf "local" (= localhost für den Server)
if 'database' in config:
    config['database']['active'] = 'local'

    # Stelle sicher dass local config korrekt ist
    if 'local' in config['database']:
        config['database']['local']['host'] = 'localhost'
        config['database']['local']['port'] = 5432
        config['database']['local']['database'] = 'postgres'
        config['database']['local']['user'] = 'mt5user'
        config['database']['local']['password'] = '1234'

# Speichere
with open(config_file, 'w') as f:
    json.dump(config, f, indent=4)

print("✓ Database-Config aktualisiert")
EOF

    echo -e "${GREEN}✓${NC} Konfiguration angepasst"
else
    echo -e "${RED}✗${NC} Config-Datei nicht gefunden: $CONFIG_FILE"
    exit 1
fi

echo ""

################################################################################
# TASK 7: Datenbank-Verbindung testen
################################################################################

echo -e "${YELLOW}[TASK 7/10]${NC} Datenbank-Verbindung testen..."

python3 << EOF
import psycopg2

try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        database='$DB_NAME',
        user='$DB_USER',
        password='$DB_PASS'
    )

    cur = conn.cursor()
    cur.execute('SELECT version();')
    version = cur.fetchone()[0]

    print(f"✓ Verbindung erfolgreich")
    print(f"  PostgreSQL: {version.split(',')[0]}")

    # Prüfe bars_1m Tabelle
    cur.execute("""
        SELECT COUNT(*) FROM bars_1m
    """)
    count = cur.fetchone()[0]
    print(f"  Bars in bars_1m: {count:,}")

    cur.close()
    conn.close()

except Exception as e:
    print(f"✗ Verbindung fehlgeschlagen: {e}")
    exit(1)
EOF

echo -e "${GREEN}✓${NC} Datenbank-Verbindung OK"

echo ""

################################################################################
# TASK 8: Datenbank-Schema vorbereiten
################################################################################

echo -e "${YELLOW}[TASK 8/10]${NC} Datenbank-Schema prüfen/aktualisieren..."

python3 << 'EOF'
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='postgres',
    user='mt5user',
    password='1234'
)
conn.autocommit = True
cur = conn.cursor()

# Prüfe ob bars_1m existiert
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'bars_1m'
    )
""")
bars_exists = cur.fetchone()[0]

if bars_exists:
    print("✓ Tabelle bars_1m existiert")

    # Prüfe Spalten
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'bars_1m'
        ORDER BY ordinal_position
    """)
    columns = [row[0] for row in cur.fetchall()]
    print(f"  Spalten ({len(columns)}): {', '.join(columns[:10])}...")

else:
    print("⚠ Tabelle bars_1m existiert nicht!")
    print("  Erstelle Tabelle...")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bars_1m (
            id SERIAL PRIMARY KEY,
            open_time TIMESTAMP WITH TIME ZONE NOT NULL,
            open DOUBLE PRECISION,
            high DOUBLE PRECISION,
            low DOUBLE PRECISION,
            close DOUBLE PRECISION,
            vol_ticks BIGINT,
            spread_mean DOUBLE PRECISION,
            spread_p95 DOUBLE PRECISION,
            rv DOUBLE PRECISION,
            UNIQUE(open_time)
        )
    """)

    # Index erstellen
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_bars_1m_open_time
        ON bars_1m(open_time DESC)
    """)

    print("✓ Tabelle bars_1m erstellt")

cur.close()
conn.close()
EOF

echo -e "${GREEN}✓${NC} Datenbank-Schema bereit"

echo ""

################################################################################
# TASK 9: Systemd Services erstellen (optional, empfohlen)
################################################################################

echo -e "${YELLOW}[TASK 9/10]${NC} Systemd Services erstellen..."

# Prüfe ob systemd verfügbar ist
if command -v systemctl &> /dev/null; then
    echo "Erstelle systemd Service-Dateien..."

    # Tick Collector Service
    sudo tee /etc/systemd/system/tick-collector.service > /dev/null << EOFSERVICE
[Unit]
Description=MT5 Tick Collector V2
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_DIR/bin/python scripts/start_tick_collector_v2.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/tick-collector.log
StandardError=append:/var/log/tick-collector.error.log

[Install]
WantedBy=multi-user.target
EOFSERVICE

    # Bar Aggregator Service
    sudo tee /etc/systemd/system/bar-aggregator.service > /dev/null << EOFSERVICE
[Unit]
Description=Bar Aggregator V2
After=network.target postgresql.service tick-collector.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_DIR/bin/python scripts/start_bar_aggregator_v2.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/bar-aggregator.log
StandardError=append:/var/log/bar-aggregator.error.log

[Install]
WantedBy=multi-user.target
EOFSERVICE

    # Reload systemd
    sudo systemctl daemon-reload

    echo -e "${GREEN}✓${NC} Systemd Services erstellt"
    echo ""
    echo "Services können gestartet werden mit:"
    echo "  sudo systemctl start tick-collector"
    echo "  sudo systemctl start bar-aggregator"
    echo ""
    echo "Für automatischen Start beim Boot:"
    echo "  sudo systemctl enable tick-collector"
    echo "  sudo systemctl enable bar-aggregator"

else
    echo -e "${YELLOW}⚠${NC} systemctl nicht verfügbar (kein systemd)"
    echo "Services müssen manuell gestartet werden"
fi

echo ""

################################################################################
# TASK 10: Services starten
################################################################################

echo -e "${YELLOW}[TASK 10/10]${NC} Services starten..."

# Frage Benutzer
echo ""
echo "Möchtest du die Services jetzt starten?"
echo ""
echo "Option 1: Als systemd Services (empfohlen)"
echo "Option 2: Manuell in tmux/screen Sessions"
echo "Option 3: Überspringen (manuell später starten)"
echo ""
read -p "Wähle Option (1/2/3): " OPTION

case $OPTION in
    1)
        echo "Starte systemd Services..."
        sudo systemctl start tick-collector
        sudo systemctl start bar-aggregator

        sleep 3

        echo ""
        echo "Service Status:"
        sudo systemctl status tick-collector --no-pager -l
        echo ""
        sudo systemctl status bar-aggregator --no-pager -l

        echo ""
        echo -e "${GREEN}✓${NC} Services gestartet"
        echo ""
        echo "Logs ansehen mit:"
        echo "  sudo journalctl -u tick-collector -f"
        echo "  sudo journalctl -u bar-aggregator -f"
        ;;

    2)
        echo "Starte Services manuell..."

        # Prüfe ob tmux verfügbar
        if command -v tmux &> /dev/null; then
            echo "Nutze tmux für Sessions..."

            # Tick Collector Session
            tmux new-session -d -s tick_collector "cd $PROJECT_DIR && source $VENV_DIR/bin/activate && python scripts/start_tick_collector_v2.py"

            # Bar Aggregator Session
            tmux new-session -d -s bar_aggregator "cd $PROJECT_DIR && source $VENV_DIR/bin/activate && python scripts/start_bar_aggregator_v2.py"

            echo -e "${GREEN}✓${NC} Services in tmux Sessions gestartet"
            echo ""
            echo "Sessions ansehen mit:"
            echo "  tmux attach -t tick_collector"
            echo "  tmux attach -t bar_aggregator"
            echo ""
            echo "Detach mit: Ctrl+B dann D"

        elif command -v screen &> /dev/null; then
            echo "Nutze screen für Sessions..."

            screen -dmS tick_collector bash -c "cd $PROJECT_DIR && source $VENV_DIR/bin/activate && python scripts/start_tick_collector_v2.py"
            screen -dmS bar_aggregator bash -c "cd $PROJECT_DIR && source $VENV_DIR/bin/activate && python scripts/start_bar_aggregator_v2.py"

            echo -e "${GREEN}✓${NC} Services in screen Sessions gestartet"
            echo ""
            echo "Sessions ansehen mit:"
            echo "  screen -r tick_collector"
            echo "  screen -r bar_aggregator"

        else
            echo -e "${RED}✗${NC} Weder tmux noch screen verfügbar!"
            echo "Installiere eines davon:"
            echo "  sudo apt install tmux"
            echo "  oder"
            echo "  sudo apt install screen"
        fi
        ;;

    3)
        echo "Services werden NICHT gestartet"
        echo ""
        echo "Manuelle Start-Befehle:"
        echo ""
        echo "Terminal 1 - Tick Collector:"
        echo "  cd $PROJECT_DIR"
        echo "  source $VENV_DIR/bin/activate"
        echo "  python scripts/start_tick_collector_v2.py"
        echo ""
        echo "Terminal 2 - Bar Aggregator:"
        echo "  cd $PROJECT_DIR"
        echo "  source $VENV_DIR/bin/activate"
        echo "  python scripts/start_bar_aggregator_v2.py"
        ;;

    *)
        echo -e "${RED}✗${NC} Ungültige Option"
        ;;
esac

echo ""

################################################################################
# FERTIG
################################################################################

echo ""
echo "=========================================="
echo -e "${GREEN}✓ SETUP ABGESCHLOSSEN${NC}"
echo "=========================================="
echo ""
echo "📊 Nächste Schritte:"
echo ""
echo "1. Prüfe ob Services laufen:"
echo "   ps aux | grep python"
echo ""
echo "2. Prüfe Logs:"
if command -v systemctl &> /dev/null && [ "$OPTION" = "1" ]; then
    echo "   sudo journalctl -u tick-collector -f"
    echo "   sudo journalctl -u bar-aggregator -f"
else
    echo "   tail -f /var/log/tick-collector.log"
    echo "   tail -f /var/log/bar-aggregator.log"
fi
echo ""
echo "3. Nach 5-10 Minuten Datensammlung prüfen:"
echo "   psql -h localhost -U mt5user -d postgres -c 'SELECT COUNT(*) FROM bars_1m WHERE open_time >= NOW() - INTERVAL \"1 hour\"'"
echo ""
echo "4. System-Status überwachen:"
echo "   watch -n 5 'psql -h localhost -U mt5user -d postgres -c \"SELECT COUNT(*) FROM bars_1m WHERE open_time >= NOW() - INTERVAL \\\"24 hours\\\"\"'"
echo ""
echo "=========================================="
echo ""

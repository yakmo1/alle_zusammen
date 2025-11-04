# 🔄 SYNC & RUN - Remote Server Setup Anleitung

**Ziel:** Setup-Script auf Remote-Server 212.132.105.198 übertragen und automatisch ausführen

---

## ⚡ SCHNELLSTE METHODE (1 Command)

Wenn du SSH-Zugang hast, führe dies **LOKAL** auf deinem Windows-Rechner aus:

```bash
scp REMOTE_SERVER_SETUP.sh user@212.132.105.198:/tmp/ && ssh user@212.132.105.198 "chmod +x /tmp/REMOTE_SERVER_SETUP.sh && /tmp/REMOTE_SERVER_SETUP.sh"
```

**Ersetze:**
- `user` → dein SSH-Username
- `212.132.105.198` → deine Server-IP (bereits korrekt)

✅ **Das war's!** - Script läuft automatisch auf dem Server.

---

## 📋 SCHRITT-FÜR-SCHRITT ANLEITUNG

### METHODE 1: Via SCP (Empfohlen)

**Schritt 1: Script auf Server kopieren**

Öffne PowerShell oder CMD auf deinem Windows-Rechner:

```powershell
# Navigiere zum Projektverzeichnis
cd C:\Projects\alle_zusammen

# Kopiere Script auf Server (SSH-Passwort wird abgefragt)
scp REMOTE_SERVER_SETUP.sh user@212.132.105.198:/tmp/
```

**Schritt 2: SSH zum Server**

```bash
ssh user@212.132.105.198
```

**Schritt 3: Script ausführen**

```bash
# Script ausführbar machen
chmod +x /tmp/REMOTE_SERVER_SETUP.sh

# Ausführen
/tmp/REMOTE_SERVER_SETUP.sh
```

---

### METHODE 2: Via Git (Alternative)

**Schritt 1: Committe Script zu Git**

Lokal auf Windows:

```powershell
cd C:\Projects\alle_zusammen

git add REMOTE_SERVER_SETUP.sh REMOTE_SERVER_TODO.md SYNC_AND_RUN.md
git commit -m "Add remote server setup automation"
git push origin master
```

**Schritt 2: SSH zum Server und pull**

```bash
ssh user@212.132.105.198

# Auf Server:
cd /opt/alle_zusammen
git pull origin master

# Script ausführen
chmod +x REMOTE_SERVER_SETUP.sh
./REMOTE_SERVER_SETUP.sh
```

---

### METHODE 3: Copy-Paste (Wenn kein SCP/Git)

**Schritt 1: Script-Inhalt kopieren**

1. Öffne `REMOTE_SERVER_SETUP.sh` in einem Editor
2. Kopiere den kompletten Inhalt (Ctrl+A, Ctrl+C)

**Schritt 2: SSH zum Server**

```bash
ssh user@212.132.105.198
```

**Schritt 3: Erstelle Script auf Server**

```bash
# Nano-Editor öffnen
nano /tmp/setup.sh

# Inhalt einfügen (Rechtsklick oder Shift+Insert)
# Speichern: Ctrl+O, Enter
# Schließen: Ctrl+X

# Ausführbar machen und starten
chmod +x /tmp/setup.sh
/tmp/setup.sh
```

---

## 🔐 SSH-ZUGANG EINRICHTEN (Falls noch nicht vorhanden)

### Windows: SSH mit PowerShell

**SSH installieren (falls nicht vorhanden):**

```powershell
# Prüfe ob SSH verfügbar
ssh -V

# Falls nicht: Installiere über Windows Settings
# Einstellungen → Apps → Optionale Features → OpenSSH Client
```

**Erste Verbindung:**

```powershell
ssh user@212.132.105.198
```

Beim ersten Mal:
- Fingerprint-Warnung: Tippe `yes`
- Passwort eingeben

**SSH-Key einrichten (optional, für passwortloses Login):**

```powershell
# SSH-Key generieren (falls nicht vorhanden)
ssh-keygen -t rsa -b 4096

# Public Key auf Server kopieren
type $env:USERPROFILE\.ssh\id_rsa.pub | ssh user@212.132.105.198 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

---

## 🎯 WAS PASSIERT BEIM SCRIPT-AUSFÜHREN?

Das Script führt automatisch alle 10 Tasks aus:

1. ✅ **System Check** (Python, Git, PostgreSQL)
2. ✅ **Alte Prozesse stoppen**
3. ✅ **Projekt klonen/updaten** (`git pull`)
4. ✅ **Virtual Environment** erstellen
5. ✅ **Dependencies** installieren
6. ✅ **Config** anpassen (Database → localhost)
7. ✅ **Datenbank** testen
8. ✅ **Schema** prüfen/erstellen
9. ✅ **Systemd Services** einrichten
10. ✅ **Services starten** (interaktiv)

**Dauer:** ~5-10 Minuten

**Bei Task 10** wirst du gefragt:
```
Möchtest du die Services jetzt starten?

Option 1: Als systemd Services (empfohlen)
Option 2: Manuell in tmux/screen Sessions
Option 3: Überspringen (manuell später starten)

Wähle Option (1/2/3):
```

**Empfehlung:** Wähle `1` für automatischen Start & Restart.

---

## 📊 NACH DEM SETUP: VERIFIZIERUNG

### Prüfe ob Services laufen

```bash
# Systemd-Status
sudo systemctl status tick-collector
sudo systemctl status bar-aggregator

# Oder via ps
ps aux | grep python
```

Erwartete Ausgabe:
```
● tick-collector.service - MT5 Tick Collector V2
   Active: active (running)

● bar-aggregator.service - Bar Aggregator V2
   Active: active (running)
```

### Prüfe Logs

```bash
# Live Logs
sudo journalctl -u tick-collector -f

# Oder in separatem Terminal
sudo journalctl -u bar-aggregator -f
```

### Prüfe Datensammlung (nach 5 Minuten)

```bash
psql -h localhost -U mt5user -d postgres << 'EOF'

-- Bars der letzten Stunde
SELECT COUNT(*) FROM bars_1m WHERE open_time >= NOW() - INTERVAL '1 hour';

-- Neuester Bar
SELECT MAX(open_time) FROM bars_1m;

EOF
```

**Erwartetes Ergebnis:**
- Mindestens 5 neue Bars
- Neuester Bar: < 5 Minuten alt

---

## 🔄 REMOTE UPDATES (Später)

Wenn du Code-Änderungen machst:

**Lokal (Windows):**
```powershell
cd C:\Projects\alle_zusammen
git add .
git commit -m "Update XYZ"
git push origin master
```

**Remote (Server):**
```bash
ssh user@212.132.105.198

cd /opt/alle_zusammen
git pull origin master

# Services neu starten
sudo systemctl restart tick-collector
sudo systemctl restart bar-aggregator
```

---

## 🛑 SERVICES STOPPEN/STARTEN

```bash
# Stoppen
sudo systemctl stop tick-collector
sudo systemctl stop bar-aggregator

# Starten
sudo systemctl start tick-collector
sudo systemctl start bar-aggregator

# Neu starten
sudo systemctl restart tick-collector
sudo systemctl restart bar-aggregator

# Status
sudo systemctl status tick-collector bar-aggregator
```

---

## 🔍 MONITORING

### Live Bar Counter

```bash
# Auf Server:
watch -n 5 'psql -h localhost -U mt5user -d postgres -c "SELECT COUNT(*) FROM bars_1m WHERE open_time >= NOW() - INTERVAL '\''1 hour'\''"'
```

Zeigt alle 5 Sekunden die Anzahl neuer Bars der letzten Stunde.

### Dashboard (von Windows aus)

Du kannst auch von deinem Windows-Rechner aus die Datenbank überwachen:

```python
# Python Script auf Windows
import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    host='212.132.105.198',
    port=5432,
    database='postgres',
    user='mt5user',
    password='1234'
)

cur = conn.cursor()

cur.execute("""
    SELECT
        COUNT(*) as total_bars,
        MAX(open_time) as latest_bar
    FROM bars_1m
    WHERE open_time >= NOW() - INTERVAL '1 hour'
""")

result = cur.fetchone()
print(f"Neue Bars (letzte Stunde): {result[0]}")
print(f"Neuester Bar: {result[1]}")

cur.close()
conn.close()
```

---

## 📞 HILFE & SUPPORT

### Script läuft nicht?

**Prüfe:**
```bash
# Script-Berechtigungen
ls -la /tmp/REMOTE_SERVER_SETUP.sh

# Sollte sein: -rwxr-xr-x (ausführbar)

# Falls nicht:
chmod +x /tmp/REMOTE_SERVER_SETUP.sh
```

### Errors im Script?

**Debug-Mode:**
```bash
# Script mit Debug-Output ausführen
bash -x /tmp/REMOTE_SERVER_SETUP.sh
```

### Services starten nicht?

**Manuelle Diagnose:**
```bash
# In Python-Umgebung gehen
cd /opt/alle_zusammen
source venv/bin/activate

# Script manuell testen
python scripts/start_tick_collector_v2.py

# Error-Meldungen beachten und beheben
```

### Datenbank-Probleme?

**PostgreSQL prüfen:**
```bash
# Läuft PostgreSQL?
sudo systemctl status postgresql

# Starten
sudo systemctl start postgresql

# Verbindung testen
psql -h localhost -U mt5user -d postgres -c "SELECT version();"
```

---

## ✅ SUCCESS CHECKLIST

Nach dem Setup sollte alles grün sein:

- [x] SSH-Verbindung funktioniert
- [x] Script auf Server kopiert
- [x] Script erfolgreich ausgeführt (alle 10 Tasks ✓)
- [x] Services laufen (systemctl status)
- [x] Logs zeigen keine Errors
- [x] Nach 5 Min: Neue Bars in Datenbank
- [x] Nach 1h: ~60 neue Bars
- [x] Nach 24h: ~1440 neue Bars

---

## 🎯 NÄCHSTE SCHRITTE (Nach erfolgreichem Setup)

1. **24h warten** - Lass System Daten sammeln
2. **Qualität prüfen** - Nutze `data_quality_check.py`
3. **ML Training** - Starte Model-Training mit neuen Daten
4. **Monitoring** - Richte Dashboard ein

Siehe [PROJEKT_STATUS.md](PROJEKT_STATUS.md) für weitere Phasen.

---

**Viel Erfolg! 🚀**

*Bei Fragen: Prüfe REMOTE_SERVER_TODO.md für detaillierte Troubleshooting-Schritte*

"""
Simple Dashboard Starter
Startet das Matrix Dashboard ohne Encoding-Probleme
"""

import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Change to project root
project_root = Path(__file__).parent.parent
os.chdir(project_root)

# Add to path
sys.path.insert(0, str(project_root))

print("=" * 70)
print("TRADING SYSTEM - Matrix Dashboard")
print("=" * 70)
print()
print("Dashboard wird gestartet...")
print("URL: http://localhost:8000")
print("Zum Stoppen: Strg + C")
print()
print("=" * 70)

# Import and run dashboard
try:
    from dashboards.matrix_dashboard import unified_master_dashboard

    # Patch print statements to avoid emoji issues
    import builtins
    original_print = builtins.print

    def safe_print(*args, **kwargs):
        try:
            original_print(*args, **kwargs)
        except UnicodeEncodeError:
            # Remove emojis and retry
            safe_args = []
            for arg in args:
                if isinstance(arg, str):
                    # Remove emojis (simple approach)
                    safe_arg = arg.encode('ascii', 'ignore').decode('ascii')
                    safe_args.append(safe_arg)
                else:
                    safe_args.append(arg)
            original_print(*safe_args, **kwargs)

    builtins.print = safe_print

    # Start dashboard
    print("Initialisiere Dashboard-Komponenten...")
    unified_master_dashboard.initialize_dashboard()

    print("Starte Flask-Server...")
    unified_master_dashboard.socketio.run(
        unified_master_dashboard.app,
        host='0.0.0.0',
        port=8000,
        debug=False,
        allow_unsafe_werkzeug=True
    )

except KeyboardInterrupt:
    print("\nDashboard wird beendet...")
except Exception as e:
    print(f"\nFEHLER: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

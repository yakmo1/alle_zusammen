"""
System Orchestrator
Startet und verwaltet alle System-Komponenten
"""

import sys
import os
import time
import subprocess
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger, log_exception
from src.utils.config_loader import get_config

logger = get_logger('system_orchestrator')

# Process Management
processes: Dict[str, subprocess.Popen] = {}
shutdown_requested = False


def signal_handler(sig, frame):
    """Signal Handler für graceful shutdown"""
    global shutdown_requested
    logger.info("Shutdown signal received")
    shutdown_requested = True
    stop_all_components()
    sys.exit(0)


def start_process(name: str, command: List[str], cwd: str = None) -> subprocess.Popen:
    """
    Startet einen Prozess

    Args:
        name: Prozess Name
        command: Command als Liste
        cwd: Working Directory

    Returns:
        subprocess.Popen
    """
    try:
        logger.info(f"Starting {name}...")

        if cwd is None:
            cwd = Path(__file__).parent.parent

        # Python-Interpreter Path
        python_exe = sys.executable

        # Command mit Python-Interpreter
        if command[0].endswith('.py'):
            command = [python_exe] + command

        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        processes[name] = process
        logger.info(f"✓ {name} started (PID: {process.pid})")

        return process

    except Exception as e:
        log_exception(logger, e, f"Failed to start {name}")
        return None


def stop_process(name: str):
    """
    Stoppt einen Prozess

    Args:
        name: Prozess Name
    """
    if name in processes:
        process = processes[name]
        logger.info(f"Stopping {name} (PID: {process.pid})...")

        try:
            process.terminate()
            process.wait(timeout=10)
            logger.info(f"✓ {name} stopped")
        except subprocess.TimeoutExpired:
            logger.warning(f"{name} did not stop gracefully, killing...")
            process.kill()
            process.wait()
            logger.info(f"✓ {name} killed")
        except Exception as e:
            log_exception(logger, e, f"Error stopping {name}")

        del processes[name]


def stop_all_components():
    """Stoppt alle Komponenten"""
    logger.info("Stopping all components...")

    for name in list(processes.keys()):
        stop_process(name)

    logger.info("✓ All components stopped")


def check_process_health(name: str) -> bool:
    """
    Prüft ob Prozess läuft

    Args:
        name: Prozess Name

    Returns:
        True wenn Prozess läuft
    """
    if name not in processes:
        return False

    process = processes[name]
    return process.poll() is None


def start_all_components():
    """Startet alle System-Komponenten"""

    logger.info("=" * 60)
    logger.info("Starting Trading System")
    logger.info("=" * 60)

    config = get_config()
    root_dir = Path(__file__).parent.parent

    # Component Definitions
    # Format: (name, command, enabled)
    components = [
        # Data Pipeline
        ('tick_collector', ['src/data/tick_collector.py'], True),
        ('bar_builder', ['src/data/bar_builder.py'], True),
        ('feature_calculator', ['src/data/feature_calculator.py'], True),

        # ML System
        ('ml_inference', ['scripts/run_inference.py'], True),

        # Trading Engine (nur aktivieren wenn Trading erlaubt ist)
        # Uncomment wenn Trading aktiv werden soll:
        # ('signal_generator', ['scripts/run_signals.py'], False),
        # ('order_executor', ['scripts/run_executor.py'], False),

        # Dashboard
        ('matrix_dashboard', ['scripts/start_dashboard.py'], True),
    ]

    started_components = []

    for name, command, enabled in components:
        if not enabled:
            logger.info(f"⊘ {name} is disabled")
            continue

        process = start_process(name, command, cwd=root_dir)
        if process:
            started_components.append(name)
            time.sleep(2)  # Warten zwischen Starts
        else:
            logger.error(f"✗ Failed to start {name}")

    logger.info("\n" + "=" * 60)
    logger.info(f"Started {len(started_components)} components")
    logger.info("=" * 60)

    for name in started_components:
        process = processes[name]
        logger.info(f"  ✓ {name} (PID: {process.pid})")

    logger.info("\n" + "=" * 60)
    logger.info("System Status:")
    logger.info("  Matrix Dashboard: http://localhost:5000")
    logger.info("  Analytics Dashboard: http://localhost:8501")
    logger.info("  Health Monitor: http://localhost:8502")
    logger.info("=" * 60)

    return started_components


def monitor_components():
    """Überwacht laufende Komponenten"""

    logger.info("\n### Monitoring Components ###")
    logger.info("Press Ctrl+C to stop the system\n")

    check_interval = 30  # Sekunden

    while not shutdown_requested:
        try:
            time.sleep(check_interval)

            # Check all processes
            for name in list(processes.keys()):
                if not check_process_health(name):
                    logger.error(f"✗ {name} has stopped unexpectedly")

                    # Auto-Restart (optional)
                    # logger.info(f"Attempting to restart {name}...")
                    # restart_component(name)

            # Log Status
            alive_count = sum(1 for name in processes if check_process_health(name))
            logger.info(f"Status: {alive_count}/{len(processes)} components running")

        except KeyboardInterrupt:
            logger.info("\nKeyboard interrupt received")
            break
        except Exception as e:
            log_exception(logger, e, "Error in monitoring loop")


def main():
    """Main Entry Point"""

    # Signal Handler registrieren
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Validiere Config
        config = get_config()
        config.validate()
        logger.info("✓ Configuration valid")

        # Starte Komponenten
        started_components = start_all_components()

        if not started_components:
            logger.error("No components started, exiting")
            sys.exit(1)

        # Monitoring Loop
        monitor_components()

    except KeyboardInterrupt:
        logger.info("\nShutdown requested")
    except Exception as e:
        log_exception(logger, e, "System error")
    finally:
        stop_all_components()
        logger.info("System shutdown complete")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║          TRADING SYSTEM UNIFIED v1.0.0                     ║
    ║                                                            ║
    ║          AI-Powered Autonomous Trading System              ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    main()

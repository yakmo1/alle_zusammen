"""
Production Server Startup Script
Starts all necessary services for 24/7 data collection and signal generation

IMPORTANT: Run this on Windows Server 2012 only!
This script is designed for production use with 24/7 uptime.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import time
import psutil
import logging
from datetime import datetime
import json
import os

# Setup logging
log_dir = Path(__file__).parent.parent / 'logs' / 'server'
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'production_server_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('ProductionServer')


class ProductionServerManager:
    """Manages all production services on Windows Server"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.scripts_dir = self.base_dir / 'scripts'
        self.logs_dir = self.base_dir / 'logs' / 'scripts'
        self.processes = {}

        # Ensure logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def start_service(self, name: str, script_path: str, description: str):
        """Start a service as background process"""
        logger.info(f"Starting {name}: {description}")

        stdout_log = self.logs_dir / f'{name}_stdout.log'
        stderr_log = self.logs_dir / f'{name}_stderr.log'

        try:
            with open(stdout_log, 'a') as stdout, open(stderr_log, 'a') as stderr:
                process = subprocess.Popen(
                    [sys.executable, script_path],
                    stdout=stdout,
                    stderr=stderr,
                    cwd=self.base_dir
                )

            self.processes[name] = {
                'process': process,
                'pid': process.pid,
                'script': script_path,
                'description': description,
                'started_at': datetime.now(),
                'stdout_log': str(stdout_log),
                'stderr_log': str(stderr_log)
            }

            # Wait a bit to check if process started successfully
            time.sleep(2)

            if process.poll() is None:
                logger.info(f"✓ {name} started successfully (PID: {process.pid})")
                return True
            else:
                logger.error(f"✗ {name} failed to start (exit code: {process.returncode})")
                return False

        except Exception as e:
            logger.error(f"✗ Error starting {name}: {e}")
            return False

    def stop_service(self, name: str):
        """Stop a service"""
        if name not in self.processes:
            logger.warning(f"{name} is not running")
            return

        proc_info = self.processes[name]
        process = proc_info['process']

        logger.info(f"Stopping {name} (PID: {proc_info['pid']})...")

        try:
            # Try graceful shutdown first
            process.terminate()

            # Wait up to 10 seconds for graceful shutdown
            try:
                process.wait(timeout=10)
                logger.info(f"✓ {name} stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if necessary
                logger.warning(f"Forcing kill of {name}...")
                process.kill()
                process.wait()
                logger.info(f"✓ {name} killed")

            del self.processes[name]

        except Exception as e:
            logger.error(f"Error stopping {name}: {e}")

    def check_services(self):
        """Check if all services are running"""
        all_running = True

        for name, info in list(self.processes.items()):
            process = info['process']

            if process.poll() is not None:
                logger.error(f"✗ {name} has stopped (exit code: {process.returncode})")
                all_running = False

                # Try to restart
                logger.info(f"Attempting to restart {name}...")
                del self.processes[name]
                self.start_service(name, info['script'], info['description'])

        return all_running

    def save_state(self):
        """Save current state to file"""
        state_file = self.base_dir / 'server' / 'production_state.json'

        state = {
            'timestamp': datetime.now().isoformat(),
            'services': {}
        }

        for name, info in self.processes.items():
            state['services'][name] = {
                'pid': info['pid'],
                'started_at': info['started_at'].isoformat(),
                'running': info['process'].poll() is None,
                'description': info['description']
            }

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def stop_all(self):
        """Stop all services"""
        logger.info("Stopping all services...")

        for name in list(self.processes.keys()):
            self.stop_service(name)

        logger.info("All services stopped")


def main():
    """Main entry point"""
    logger.info("=" * 70)
    logger.info("PRODUCTION SERVER MANAGER")
    logger.info("Windows Server 2012 - 24/7 Data Collection & Trading")
    logger.info("=" * 70)
    logger.info("")

    # Check if running on server (optional safety check)
    hostname = os.environ.get('COMPUTERNAME', 'unknown')
    logger.info(f"Running on: {hostname}")

    # Warning for production
    logger.warning("=" * 70)
    logger.warning("PRODUCTION MODE - This will start 24/7 services")
    logger.warning("Press CTRL+C within 5 seconds to cancel")
    logger.warning("=" * 70)

    try:
        time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Cancelled by user")
        return

    manager = ProductionServerManager()

    # Start services in order
    services = [
        {
            'name': 'tick_collector_v2',
            'script': str(manager.scripts_dir / 'start_tick_collector_v2.py'),
            'description': 'Collects live tick data from MT5'
        },
        {
            'name': 'bar_aggregator_v2',
            'script': str(manager.scripts_dir / 'start_bar_aggregator_v2.py'),
            'description': 'Aggregates ticks into OHLC bars'
        },
        {
            'name': 'signal_generator',
            'script': str(manager.scripts_dir / 'start_signal_generator.py'),
            'description': 'Generates trading signals from ML models'
        }
    ]

    logger.info("")
    logger.info("Starting production services...")
    logger.info("")

    for service in services:
        success = manager.start_service(
            service['name'],
            service['script'],
            service['description']
        )

        if not success:
            logger.error(f"Failed to start {service['name']}")
            logger.error("Stopping all services and exiting...")
            manager.stop_all()
            return

        time.sleep(1)  # Small delay between service starts

    logger.info("")
    logger.info("=" * 70)
    logger.info("ALL SERVICES STARTED SUCCESSFULLY")
    logger.info("=" * 70)
    logger.info("")

    # Print status
    logger.info("Running Services:")
    for name, info in manager.processes.items():
        logger.info(f"  • {name} (PID: {info['pid']}) - {info['description']}")

    logger.info("")
    logger.info("Log Files:")
    for name, info in manager.processes.items():
        logger.info(f"  • {name}: {info['stdout_log']}")

    logger.info("")
    logger.info("Server is now running 24/7. Press CTRL+C to stop all services.")
    logger.info("")

    # Monitor loop
    try:
        check_interval = 60  # Check every 60 seconds

        while True:
            time.sleep(check_interval)

            # Check services
            all_running = manager.check_services()

            # Save state
            manager.save_state()

            # Log status every 15 minutes
            if datetime.now().minute % 15 == 0:
                logger.info(f"Status check: {len(manager.processes)} services running")

    except KeyboardInterrupt:
        logger.info("")
        logger.info("Shutdown requested by user")

    except Exception as e:
        logger.error(f"Error in monitoring loop: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        manager.stop_all()
        logger.info("Production server stopped")


if __name__ == '__main__':
    main()

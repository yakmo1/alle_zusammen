"""
Start Trade Monitor
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import MetaTrader5 as mt5
from src.utils.logger import get_logger
import time
logger = get_logger('TradeMonitorService')
def main():
    logger.info("TRADE MONITOR SERVICE")
    if not mt5.initialize():
        return
    try:
        logger.info("Running...")
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Stopped")
if __name__ == '__main__':
    main()

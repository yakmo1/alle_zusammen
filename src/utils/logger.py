"""
Logging System für das Trading System
Zentrale Logging-Konfiguration mit Rotation und Formatierung
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime

class ColoredFormatter(logging.Formatter):
    """Farbiger Formatter für Console Output"""

    # ANSI Color Codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Formatiert Log Record mit Farbe"""
        # Original formatieren
        log_message = super().format(record)

        # Farbe hinzufügen
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        return f"{color}{log_message}{reset}"


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    log_level: str = 'INFO',
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console: bool = True
) -> logging.Logger:
    """
    Erstellt und konfiguriert einen Logger

    Args:
        name: Logger Name
        log_file: Pfad zur Log-Datei (None = kein File Logging)
        log_level: Log Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximale Größe der Log-Datei
        backup_count: Anzahl Backup-Dateien
        console: Console Logging aktivieren

    Returns:
        Konfigurierter Logger
    """
    # Logger erstellen
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Verhindere doppelte Handler
    if logger.handlers:
        return logger

    # Format
    detailed_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_format = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # File Handler
    if log_file:
        # Log-Verzeichnis erstellen wenn nicht vorhanden
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Alle Levels in File
        file_handler.setFormatter(detailed_format)
        logger.addHandler(file_handler)

    # Console Handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(simple_format)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Holt einen Logger (erstellt ihn wenn nötig)

    Args:
        name: Logger Name (None = root logger)

    Returns:
        Logger Instance
    """
    if name is None:
        name = 'trading_system'

    logger = logging.getLogger(name)

    # Wenn Logger noch nicht konfiguriert, mit Defaults initialisieren
    if not logger.handlers:
        from .config_loader import get_config

        try:
            config = get_config()
            log_config = config.get_log_config()

            setup_logger(
                name=name,
                log_file=log_config.get('file'),
                log_level=log_config.get('level', 'INFO'),
                max_bytes=log_config.get('max_bytes', 10 * 1024 * 1024),
                backup_count=log_config.get('backup_count', 5)
            )
        except Exception as e:
            # Fallback auf Basic Config
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            logger.warning(f"Could not load config, using basic logging: {e}")

    return logger


class LoggerMixin:
    """Mixin für Klassen die Logging brauchen"""

    @property
    def logger(self) -> logging.Logger:
        """Holt Logger für diese Klasse"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """
    Loggt eine Exception mit Stack Trace

    Args:
        logger: Logger Instance
        exc: Exception
        context: Zusätzlicher Kontext
    """
    if context:
        logger.error(f"{context}: {type(exc).__name__}: {exc}", exc_info=True)
    else:
        logger.error(f"{type(exc).__name__}: {exc}", exc_info=True)


def log_trade(
    logger: logging.Logger,
    action: str,
    symbol: str,
    volume: float,
    price: float,
    sl: float = None,
    tp: float = None,
    comment: str = ""
):
    """
    Loggt einen Trade

    Args:
        logger: Logger Instance
        action: Trade Action (BUY/SELL/CLOSE)
        symbol: Trading Symbol
        volume: Volume
        price: Preis
        sl: Stop Loss
        tp: Take Profit
        comment: Zusätzlicher Kommentar
    """
    msg = f"TRADE: {action} {volume} {symbol} @ {price}"

    if sl:
        msg += f" | SL: {sl}"
    if tp:
        msg += f" | TP: {tp}"
    if comment:
        msg += f" | {comment}"

    logger.info(msg)


def log_signal(
    logger: logging.Logger,
    signal: str,
    symbol: str,
    confidence: float,
    horizon: str,
    reason: str = ""
):
    """
    Loggt ein Trading Signal

    Args:
        logger: Logger Instance
        signal: Signal Type (BUY/SELL/HOLD)
        symbol: Trading Symbol
        confidence: Confidence Score
        horizon: Forecast Horizon
        reason: Grund für Signal
    """
    msg = f"SIGNAL: {signal} {symbol} | Confidence: {confidence:.2%} | Horizon: {horizon}"

    if reason:
        msg += f" | {reason}"

    logger.info(msg)


def log_performance(
    logger: logging.Logger,
    metric: str,
    value: float,
    context: str = ""
):
    """
    Loggt Performance Metriken

    Args:
        logger: Logger Instance
        metric: Metrik Name
        value: Metrik Wert
        context: Kontext
    """
    msg = f"PERFORMANCE: {metric}={value:.4f}"

    if context:
        msg += f" | {context}"

    logger.info(msg)


if __name__ == "__main__":
    # Test
    print("=== Logger Test ===\n")

    # Basic Logger
    logger = setup_logger(
        name='test_logger',
        log_file='logs/test.log',
        log_level='DEBUG',
        console=True
    )

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Trade Log
    print("\n=== Trade Log Test ===\n")
    log_trade(
        logger,
        action='BUY',
        symbol='EURUSD',
        volume=0.1,
        price=1.0850,
        sl=1.0800,
        tp=1.0900,
        comment='ML Signal'
    )

    # Signal Log
    print("\n=== Signal Log Test ===\n")
    log_signal(
        logger,
        signal='BUY',
        symbol='EURUSD',
        confidence=0.85,
        horizon='5min',
        reason='Strong uptrend detected'
    )

    # Exception Log
    print("\n=== Exception Log Test ===\n")
    try:
        raise ValueError("Test exception")
    except Exception as e:
        log_exception(logger, e, "Testing exception logging")

    print("\n✓ Logger test complete")

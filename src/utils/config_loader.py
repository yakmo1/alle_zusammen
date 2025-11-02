"""
Configuration Loader für das Trading System
Lädt und validiert config.json und .env Dateien
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

class ConfigLoader:
    """Zentrale Konfigurationsverwaltung"""

    def __init__(self, config_path: str = None, env_path: str = None):
        """
        Initialisiert den Config Loader

        Args:
            config_path: Pfad zur config.json (optional)
            env_path: Pfad zur .env (optional)
        """
        # Projekt-Root finden
        self.root_dir = Path(__file__).parent.parent.parent

        # Config-Pfad
        if config_path is None:
            config_path = self.root_dir / "config" / "config.json"
        self.config_path = Path(config_path)

        # Env-Pfad
        if env_path is None:
            env_path = self.root_dir / ".env"
        self.env_path = Path(env_path)

        # Config laden
        self.config = self._load_config()
        self.env = self._load_env()

    def _load_config(self) -> Dict[str, Any]:
        """Lädt die config.json"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        return config

    def _load_env(self) -> Dict[str, str]:
        """Lädt die .env Datei"""
        if not self.env_path.exists():
            print(f"Warning: .env file not found: {self.env_path}")
            return {}

        load_dotenv(self.env_path)
        return dict(os.environ)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Holt einen Wert aus der Config

        Args:
            key: Key in Dot-Notation (z.B. "database.local.host")
            default: Default-Wert wenn Key nicht existiert

        Returns:
            Wert aus Config oder default
        """
        keys = key.split('.')
        value = self.config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_env(self, key: str, default: str = None) -> str:
        """
        Holt einen Wert aus den Environment Variables

        Args:
            key: Environment Variable Name
            default: Default-Wert wenn Variable nicht existiert

        Returns:
            Wert aus .env oder default
        """
        return os.getenv(key, default)

    def get_database_config(self, db_type: str = None) -> Dict[str, Any]:
        """
        Holt Database-Config

        Args:
            db_type: 'local' oder 'remote' (None = active)

        Returns:
            Database Configuration Dict
        """
        if db_type is None:
            db_type = self.get('database.active', 'local')

        return self.get(f'database.{db_type}', {})

    def get_mt5_config(self) -> Dict[str, Any]:
        """
        Holt MT5-Config

        Returns:
            MT5 Configuration Dict
        """
        config = self.get('mt5', {})

        # Override mit Environment Variables wenn vorhanden
        if self.get_env('MT5_LOGIN'):
            config['login'] = int(self.get_env('MT5_LOGIN'))
        if self.get_env('MT5_PASSWORD'):
            config['password'] = self.get_env('MT5_PASSWORD')
        if self.get_env('MT5_SERVER'):
            config['server'] = self.get_env('MT5_SERVER')
        if self.get_env('MT5_PATH'):
            config['path'] = self.get_env('MT5_PATH')

        return config

    def get_trading_config(self) -> Dict[str, Any]:
        """
        Holt Trading-Config

        Returns:
            Trading Configuration Dict
        """
        return self.get('trading', {})

    def get_ml_config(self) -> Dict[str, Any]:
        """
        Holt ML-Config

        Returns:
            ML Configuration Dict
        """
        return self.get('modeling', {})

    def get_symbols(self) -> list:
        """Holt Liste der Trading Symbols"""
        return self.get('data.symbols', ['EURUSD'])

    def get_bar_types(self) -> list:
        """Holt Liste der Bar Types"""
        return self.get('data.bar_types', ['1m', '5m', '15m', '1h'])

    def is_auto_trading_enabled(self) -> bool:
        """Prüft ob Auto-Trading aktiviert ist"""
        return self.get('trading.enable_auto_trading', False)

    def get_log_config(self) -> Dict[str, Any]:
        """
        Holt Logging-Config

        Returns:
            Logging Configuration Dict
        """
        return {
            'level': self.get_env('LOG_LEVEL', 'INFO'),
            'file': self.get_env('LOG_FILE', 'logs/trading_system.log'),
            'max_bytes': int(self.get_env('LOG_MAX_BYTES', '10485760')),
            'backup_count': int(self.get_env('LOG_BACKUP_COUNT', '5'))
        }

    def validate(self) -> bool:
        """
        Validiert die Konfiguration

        Returns:
            True wenn Config valide ist

        Raises:
            ValueError wenn Config ungültig
        """
        # Prüfe kritische Felder
        required_fields = [
            'database',
            'mt5',
            'trading',
            'modeling'
        ]

        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")

        # Prüfe Database Config
        db_config = self.get_database_config()
        required_db_fields = ['host', 'port', 'database', 'user', 'password']
        for field in required_db_fields:
            if field not in db_config:
                raise ValueError(f"Missing required database field: {field}")

        # Prüfe MT5 Config
        mt5_config = self.get_mt5_config()
        required_mt5_fields = ['login', 'password', 'server']
        for field in required_mt5_fields:
            if field not in mt5_config:
                raise ValueError(f"Missing required MT5 field: {field}")

        return True

    def __repr__(self) -> str:
        """String Representation"""
        return f"ConfigLoader(config_path={self.config_path})"


# Singleton Instance
_config_loader = None

def get_config() -> ConfigLoader:
    """
    Holt die globale Config Loader Instance

    Returns:
        ConfigLoader Instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


if __name__ == "__main__":
    # Test
    config = ConfigLoader()

    print("=== Configuration Test ===")
    print(f"Database Config: {config.get_database_config()}")
    print(f"MT5 Config: {config.get_mt5_config()}")
    print(f"Trading Config: {config.get_trading_config()}")
    print(f"Symbols: {config.get_symbols()}")
    print(f"Auto Trading: {config.is_auto_trading_enabled()}")

    print("\n=== Validation ===")
    try:
        config.validate()
        print("✓ Configuration is valid")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")

"""
Configuration management for Polytrader.

Loads configuration from YAML files with environment variable substitution.
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager with YAML loading and env var support."""

    _instance: Optional["Config"] = None
    _config: dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._config:
            self.load()

    def load(self, config_path: Optional[str] = None) -> None:
        """Load configuration from YAML file."""
        # Load .env file if exists
        load_dotenv()

        # Find config file
        if config_path:
            path = Path(config_path)
        else:
            # Search in common locations
            search_paths = [
                Path.cwd() / "config.yaml",
                Path.cwd() / "config.yml",
                Path(__file__).parent.parent / "config.yaml",
                Path.home() / ".polytrader" / "config.yaml",
            ]
            path = None
            for p in search_paths:
                if p.exists():
                    path = p
                    break

        if path and path.exists():
            with open(path) as f:
                raw_config = yaml.safe_load(f)
                self._config = self._substitute_env_vars(raw_config)
        else:
            # Use defaults
            self._config = self._get_defaults()

    def _substitute_env_vars(self, obj: Any) -> Any:
        """Recursively substitute ${VAR} patterns with environment variables."""
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Match ${VAR} or ${VAR:default} patterns
            pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"

            def replace(match):
                var_name = match.group(1)
                default = match.group(2)
                return os.environ.get(var_name, default if default else "")

            return re.sub(pattern, replace, obj)
        return obj

    def _get_defaults(self) -> dict[str, Any]:
        """Return default configuration."""
        return {
            "mode": "paper",
            "api": {
                "private_key": "",
                "api_key": "",
                "api_secret": "",
                "api_passphrase": "",
                "chain_id": 137,
                "host": "https://clob.polymarket.com",
            },
            "websocket": {
                "auto_reconnect": True,
                "reconnect_delay": 5,
                "ping_interval": 5,  # Polymarket requires PING every 5 seconds
            },
            "logging": {
                "level": "INFO",
                "file": "logs/polytrader.log",
                "console_format": "rich",
            },
            "storage": {
                "data_dir": "./data",
                "database": "polytrader.db",
                "csv_dir": "exports",
            },
            "paper": {
                "starting_balance": 10000.0,
                "slippage": 0.001,
                "fill_delay": 0.5,
            },
            "strategy": {
                "default_size": 100.0,
                "max_position": 1000.0,
                "stop_loss": 0.0,
                "take_profit": 0.0,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation (e.g., 'api.host')."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation."""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    @property
    def mode(self) -> str:
        """Get trading mode (paper/live)."""
        return self.get("mode", "paper")

    @property
    def is_paper(self) -> bool:
        """Check if in paper trading mode."""
        return self.mode == "paper"

    @property
    def is_live(self) -> bool:
        """Check if in live trading mode."""
        return self.mode == "live"

    @property
    def private_key(self) -> str:
        """Get private key for signing transactions."""
        return self.get("api.private_key", "")

    @property
    def api_key(self) -> str:
        """Get API key for WebSocket authentication."""
        return self.get("api.api_key", "")

    @property
    def api_secret(self) -> str:
        """Get API secret for WebSocket authentication."""
        return self.get("api.api_secret", "")

    @property
    def api_passphrase(self) -> str:
        """Get API passphrase for WebSocket authentication."""
        return self.get("api.api_passphrase", "")

    @property
    def chain_id(self) -> int:
        """Get blockchain chain ID."""
        return self.get("api.chain_id", 137)

    @property
    def host(self) -> str:
        """Get API host URL."""
        return self.get("api.host", "https://clob.polymarket.com")

    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        return Path(self.get("storage.data_dir", "./data"))

    @property
    def database_path(self) -> Path:
        """Get SQLite database path."""
        return self.data_dir / self.get("storage.database", "polytrader.db")

    @property
    def csv_dir(self) -> Path:
        """Get CSV export directory path."""
        return self.data_dir / self.get("storage.csv_dir", "exports")

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.get("logging.level", "INFO")

    @property
    def log_file(self) -> Path:
        """Get log file path."""
        return self.data_dir / self.get("logging.file", "logs/polytrader.log")

    def to_dict(self) -> dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()

    def __repr__(self) -> str:
        return f"Config(mode={self.mode}, host={self.host})"


# Global config instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


"""
Config Loader Utility
Loads YAML configuration files
"""

import yaml
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """Loads and caches configuration files."""

    def __init__(self):
        """Initialize config loader."""
        self._cache = {}

    def load(self, config_path: str) -> Dict[str, Any]:
        """
        Load YAML configuration file.

        Args:
            config_path: Path to YAML config file

        Returns:
            Dictionary with configuration
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Return from cache if available
        cache_key = str(config_path.absolute())
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load and cache
        with open(config_path) as f:
            config = yaml.safe_load(f)

        self._cache[cache_key] = config
        return config

    def get(self, key: str, default=None) -> Any:
        """
        Get value from cached config.

        Args:
            key: Config key
            default: Default value if not found

        Returns:
            Config value or default
        """
        for config in self._cache.values():
            if key in config:
                return config[key]
        return default

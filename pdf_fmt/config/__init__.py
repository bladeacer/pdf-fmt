"""Config loading with modification time caching."""

import os
from typing import Any, Dict, Optional

from .loader import _load_config
from .paths import CONFIG_FILENAME, find_config_file

_CONFIG_CACHE: Dict[str, Any] = {}
_CONFIG_MTIME_CACHE: float = 0.0
_CONFIG_CACHE_PATH: Optional[str] = None


def clear_config_cache() -> None:
    """Clears the cached config data, path and modification time."""
    global _CONFIG_CACHE, _CONFIG_MTIME_CACHE, _CONFIG_CACHE_PATH
    _CONFIG_CACHE = {}
    _CONFIG_MTIME_CACHE = 0.0
    _CONFIG_CACHE_PATH = None


def load_config() -> Dict[str, Any]:
    """Loads config data, utilizing modification time caching."""
    global _CONFIG_CACHE, _CONFIG_MTIME_CACHE, _CONFIG_CACHE_PATH

    file_path = find_config_file()

    if not file_path:
        print(f"Warning: Configuration file '{CONFIG_FILENAME}' not found. Using defaults.")
        return {}

    try:
        current_mtime = os.path.getmtime(file_path)
    except OSError:
        print(f"Warning: Configuration file '{file_path}' is inaccessible. Using defaults.")
        return {}

    if (
        _CONFIG_CACHE
        and file_path == _CONFIG_CACHE_PATH
        and current_mtime == _CONFIG_MTIME_CACHE
    ):
        print("INFO: Loaded configuration from cache (mtime check successful).")
        return _CONFIG_CACHE

    config = _load_config(file_path)

    _CONFIG_CACHE = config
    _CONFIG_CACHE_PATH = file_path
    _CONFIG_MTIME_CACHE = current_mtime
    print(f"INFO: Loaded configuration from: {file_path}")

    return config


__all__ = [
    "CONFIG_FILENAME",
    "_load_config",
    "clear_config_cache",
    "find_config_file",
    "load_config",
]

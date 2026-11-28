import os
import platform
from typing import Any, Dict, Optional

import yaml

CONFIG_FILENAME = "pdf-fmt.yaml"

_CONFIG_CACHE: Dict[str, Any] = {}
_CONFIG_MTIME_CACHE: float = 0.0
_CONFIG_CACHE_PATH: Optional[str] = None


def find_config_file() -> Optional[str]:
    """Searches for the config file using ENV, XDG standard, then CWD."""
    env_path = os.environ.get('PDF_FMT_CONFIG_PATH')
    if env_path and os.path.exists(env_path):
        return env_path

    if platform.system() == 'Windows':
        config_dir = os.environ.get('APPDATA')
    else:
        config_dir = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))

    if config_dir:
        xdg_path = os.path.join(config_dir, 'pdf-fmt', CONFIG_FILENAME)
        if os.path.exists(xdg_path):
            return xdg_path

    cwd_path = os.path.join(os.getcwd(), CONFIG_FILENAME)
    if os.path.exists(cwd_path):
        return cwd_path

    return None


def clear_config_cache() -> None:
    """Clears the cached config data, path and modification time."""
    global _CONFIG_CACHE, _CONFIG_MTIME_CACHE, _CONFIG_CACHE_PATH
    _CONFIG_CACHE = {}
    _CONFIG_MTIME_CACHE = 0.0
    _CONFIG_CACHE_PATH = None


def _load_config(file_path: str) -> Dict[str, Any]:
    """Internal function to load config data from a YAML file with basic validation."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

    except yaml.YAMLError as e:
        print(f"Error: Malformed YAML syntax in '{file_path}': {e}. Using defaults.\n")
        return {}

    except Exception as e:
        print(f"Error: Could not read file '{file_path}': {e}. Using defaults.\n")
        return {}

    if not isinstance(config, dict):
        if config is None:
            return {}
        else:
            print(f"Error: Configuration file '{file_path}' must have a dictionary (map) as its root element, found '{type(config).__name__}'. Using defaults.\n")
            return {}

    return config


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

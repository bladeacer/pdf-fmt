import os
import yaml
import platform
import time
from typing import Dict, Any, Optional

CONFIG_FILENAME = "pdf-fmt.yaml"

_CONFIG_CACHE: Dict[str, Any] = {}
_CONFIG_PATH_CACHE: Optional[str] = None
_CONFIG_MTIME_CACHE: float = 0.0

def find_config_file() -> Optional[str]:
    """Searches for the config file using ENV, XDG standard, then CWD."""
    global _CONFIG_PATH_CACHE
    if _CONFIG_PATH_CACHE is not None:
        return _CONFIG_PATH_CACHE

    env_path = os.environ.get('PDF_FMT_CONFIG_PATH')
    if env_path and os.path.exists(env_path):
        _CONFIG_PATH_CACHE = env_path
        return env_path

    if platform.system() == 'Windows':
        config_dir = os.environ.get('APPDATA')
    else:
        config_dir = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))

    if config_dir:
        xdg_path = os.path.join(config_dir, 'pdf-fmt', CONFIG_FILENAME)
        if os.path.exists(xdg_path):
            _CONFIG_PATH_CACHE = xdg_path
            return xdg_path

    cwd_path = os.path.join(os.getcwd(), CONFIG_FILENAME)
    if os.path.exists(cwd_path):
        _CONFIG_PATH_CACHE = cwd_path
        return cwd_path
    
    _CONFIG_PATH_CACHE = None
    return None

def _load_config(file_path: str) -> Dict[str, Any]:
    """Internal function to load config data from a YAML file without caching logic."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config if isinstance(config, dict) else {}
    except Exception as e:
        print(f"Error: Could not read or parse '{file_path}': {e}. Using defaults.")
        return {}

def load_config() -> Dict[str, Any]:
    """Loads config data, utilizing modification time caching."""
    global _CONFIG_CACHE, _CONFIG_MTIME_CACHE
    
    file_path = find_config_file()
    
    if not file_path:
        print(f"Warning: Configuration file '{CONFIG_FILENAME}' not found. Using defaults.")
        return {}
    
    try:
        current_mtime = os.path.getmtime(file_path)
    except OSError:
        print(f"Warning: Configuration file '{file_path}' is inaccessible. Using defaults.")
        return {}

    if _CONFIG_CACHE and current_mtime == _CONFIG_MTIME_CACHE:
        print(f"INFO: Loaded configuration from cache (mtime check successful).")
        return _CONFIG_CACHE

    config = _load_config(file_path)
    
    _CONFIG_CACHE = config
    _CONFIG_MTIME_CACHE = current_mtime
    print(f"INFO: Loaded configuration from: {file_path}")
    
    return config

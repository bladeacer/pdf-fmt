"""Config file discovery."""

import os
import platform
from typing import Optional

CONFIG_FILENAME = "pdf-fmt.yaml"


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

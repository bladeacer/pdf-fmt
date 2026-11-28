"""Startup environment checks."""

import ctypes
import getpass
import os
import platform
import sys

IS_CI_BUILD = os.environ.get('PDF_FMT_CI_BUILD', '0') == '1'
IS_NUITKA_COMPILED = "__compiled__" in globals()


class StartupCheckError(Exception):
    """Raised when a startup check fails."""

    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code
        super().__init__(self.message)


def check_venv() -> None:
    """Checks the `.venv` requirement."""
    if IS_NUITKA_COMPILED or getattr(sys, 'frozen', False) or IS_CI_BUILD:
        return

    if sys.prefix != sys.base_prefix:
        venv_path = sys.prefix
        if os.path.basename(venv_path) == '.venv':
            return

    message = (
        "Error: Script must be run from the '.venv' virtual environment.\n"
        "Please activate it first (e.g., 'source .venv/bin/activate')."
    )
    raise StartupCheckError(message, 1)


def check_not_root() -> None | StartupCheckError:
    """Rejects root and administrator privileges."""
    non_admin_warning: str = """
Error: Running as root is disabled for security and stability.
Please run this application as a regular user.
    """

    if platform.system() in ('Linux', 'Darwin') and os.getuid() == 0:
        raise StartupCheckError(non_admin_warning, 1)

    if platform.system() == 'Windows':
        try:
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            is_admin = getpass.getuser().lower() in ('administrator', 'admin')
        if is_admin:
            raise StartupCheckError(non_admin_warning, 1)

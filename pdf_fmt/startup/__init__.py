"""CLI setup and startup checks."""

from .checks import (
    IS_CI_BUILD,
    IS_NUITKA_COMPILED,
    StartupCheckError,
    check_not_root,
    check_venv,
)
from .cli import setup_cli
from .version import SCRIPT_VERSION, get_script_version

__all__ = [
    "IS_CI_BUILD",
    "IS_NUITKA_COMPILED",
    "SCRIPT_VERSION",
    "StartupCheckError",
    "check_not_root",
    "check_venv",
    "get_script_version",
    "setup_cli",
]

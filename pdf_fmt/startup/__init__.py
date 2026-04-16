import sys
import os
import platform
import getpass
import ctypes
import argparse
import re


def get_script_version() -> str:
    """
    Resolves version with support for:
    1. CI Environment variables (PDF_FMT_VERSION).
    2. Local root execution (./pyproject.toml).
    3. Installed package execution (../../pyproject.toml).
    """
    ci_version = os.environ.get('PDF_FMT_VERSION')
    if ci_version:
        return ci_version

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))

        candidates = [
            os.path.join(base_dir, "pyproject.toml"),
            os.path.join(base_dir, "..", "..", "pyproject.toml")
        ]

        for toml_path in candidates:
            if os.path.exists(toml_path):
                with open(toml_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match = re.search(r'version\s*=\s*"([^"]+)"', content)
                    if match:
                        return match.group(1)
    except Exception:
        pass

    return "0.1.0"


SCRIPT_VERSION = get_script_version()
IS_CI_BUILD = os.environ.get('PDF_FMT_CI_BUILD', '0') == '1'
IS_NUITKA_COMPILED = "__compiled__" in globals()


class StartupCheckError(Exception):
    """
    Custom exception raised when a critical startup environment check fails.
    """

    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code
        super().__init__(self.message)


def check_venv() -> None:
    """Checks if the script is running inside a virtual environment (.venv)."""
    if IS_NUITKA_COMPILED or getattr(sys, 'frozen', False) or IS_CI_BUILD:
        return

    is_venv_active = (sys.prefix != sys.base_prefix)

    if is_venv_active:
        venv_path = sys.prefix

        if os.path.basename(venv_path) == '.venv':
            return

    message = (
        "Error: Script must be run from the '.venv' virtual environment.\n"
        "Please activate it first (e.g., 'source .venv/bin/activate')."
    )
    raise StartupCheckError(message, 1)


def check_not_root() -> None | StartupCheckError:
    """
    Checks that the application is not running with root/administrator
    privileges.
    """

    non_admin_warning: str = """
Error: Running as root is disabled for security and stability.
Please run this application as a regular user.
    """

    if platform.system() in ('Linux', 'Darwin') and os.getuid() == 0:
        message = non_admin_warning
        raise StartupCheckError(message, 1)

    elif platform.system() == 'Windows':
        try:
            if ctypes.windll.shell32.IsUserAnAdmin():
                message = non_admin_warning
                raise StartupCheckError(message, 1)

        except Exception:
            if getpass.getuser().lower() in ('administrator', 'admin'):
                message = non_admin_warning
                raise StartupCheckError(message, 1)


def setup_cli() -> argparse.Namespace:
    """
    Sets up the argparse CLI and handles flags.
    """

    default_str: str = """pdf-fmt

Cleanly extracts and formats text from a PDF document or convertible file.
Licensed under GPLv3.
    """

    path_str: str = """
Path to the PDF or convertibel file (e.g. pptx, docx) to process.
"""

    parser = argparse.ArgumentParser(
        description=default_str,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'file_path',
        nargs='?',
        default=None,
        help=path_str
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {SCRIPT_VERSION}',
        help="Show script's version and exit."
    )
    args = parser.parse_args()

    if args.file_path is None:
        parser.print_help()
        raise StartupCheckError("", 0)
    if not os.path.exists(args.file_path):
        message = f"Error: Input file not found at path: '{args.file_path}'"
        raise StartupCheckError(message, 1)

    return args

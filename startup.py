import sys
import os
import platform
import getpass
import argparse
from typing import TYPE_CHECKING, Optional

# --- Custom Exception ---
class StartupCheckError(Exception):
    """Custom exception raised when a critical startup environment check fails."""
    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code
        super().__init__(self.message)

# --- Constants ---
SCRIPT_VERSION = "0.6.0" 
IS_CI_BUILD = os.environ.get('PDF_FMT_CI_BUILD', '0') == '1'
IS_NUITKA_COMPILED = "__compiled__" in globals()


def check_venv() -> None | StartupCheckError:
    """Checks if the script is running inside a virtual environment (.venv)."""
    if IS_NUITKA_COMPILED or getattr(sys, 'frozen', False) or IS_CI_BUILD:
        message = ("Error: Script must be run from the '.venv' virtual environment.\n"
                   "Please activate it first (e.g., 'source .venv/bin/activate').")
        return StartupCheckError(message)

    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path or not os.path.basename(venv_path) == '.venv':
        message = ("Error: Script must be run from the '.venv' virtual environment.\n"
                   "Please activate it first (e.g., 'source .venv/bin/activate').")
        raise StartupCheckError(message)

def check_not_root() -> None | StartupCheckError:
    """Checks that the application is not running with root/administrator privileges."""
    if platform.system() in ('Linux', 'Darwin'):
        if os.getuid() == 0:
            message = ("Error: Running as root is disabled for security and stability.\n"
                       "Please run this application as a regular user.")
            raise StartupCheckError(message)
            
    elif platform.system() == 'Windows':
        if getpass.getuser().lower() in ('administrator', 'admin'):
            message = "Warning: Do not run as 'Administrator'."
            raise StartupCheckError(message)

def setup_cli() -> argparse.Namespace:
    """Sets up the argparse CLI and handles flags."""
    parser = argparse.ArgumentParser(
        description="pdf-fmt\n\nCleanly extracts and formats text from a PDF document or convertible file.\nLicensed under GPLv3.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'file_path',
        nargs='?',
        default=None,
        help="Path to the PDF or convertible file (e.g., pptx, docx) to process."
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
        raise StartupCheckError("", exit_code=0)
    if not os.path.exists(args.file_path):
        message = f"Error: Input file not found at path: '{args.file_path}'"
        raise StartupCheckError(message, exit_code=1)
        
    return args

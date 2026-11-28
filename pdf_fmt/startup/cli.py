"""Argument parsing for the CLI."""

import argparse
import os
import sys

from .checks import StartupCheckError
from .version import SCRIPT_VERSION


def setup_cli() -> argparse.Namespace:
    """Parses the input path and validates it."""
    default_str: str = """pdf-fmt

Cleanly extracts and formats text from a PDF document or convertible file.
Licensed under GPLv3.
    """
    path_str: str = """
Path to the file. Use '-' or leave empty to read from stdin (pipe).
    """

    parser = argparse.ArgumentParser(
        prog='pdf-fmt',
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

    cond: bool = (args.file_path == "-" or
                  (args.file_path is None and not sys.stdin.isatty())
                  )

    if cond:
        args.file_path = "-"
        return args

    if args.file_path is None:
        parser.print_help()
        raise StartupCheckError("", 0)

    if not os.path.exists(args.file_path):
        message = f"Error: Input file not found at path: '{args.file_path}'"
        raise StartupCheckError(message, 1)

    return args

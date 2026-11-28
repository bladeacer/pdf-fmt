# Copyright (c) 2025 bladeacer
# Licensed under the GPLv3 License. See LICENSE file for details.

"""Single CLI implementation shared by every entry point."""

import os
import sys
from typing import Any, Dict

from pdf_fmt.startup import StartupCheckError, check_not_root, check_venv


def _handle_broken_pipe() -> None:
    """Redirect stdout and exit after a broken pipe."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())
    sys.stdout.close()
    os._exit(0)


def main(*, check_environment: bool = False) -> None:
    """Runs the pipeline after the selected startup checks."""
    try:
        check_not_root()
        if check_environment:
            check_venv()

        from pdf_fmt import config
        from pdf_fmt.parser import execute_main_pipeline

        settings: Dict[str, Any] = config.load_config()
        execute_main_pipeline(settings)
    except StartupCheckError as error:
        print(error.message)
        sys.exit(error.exit_code)
    except BrokenPipeError:
        _handle_broken_pipe()
    except Exception as error:
        print(f"Unknown error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

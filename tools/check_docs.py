#!/usr/bin/env python3
"""Reject em dashes in the hand-written Markdown documentation."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {"skills", ".venv", ".venv-build", ".git", "build", ".ruff_cache"}
EM_DASH = re.compile("\u2014")


def doc_files() -> list[Path]:
    """Return the Markdown files that the gate checks."""
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if not EXCLUDED_DIRS.intersection(path.relative_to(ROOT).parts)
    )


def em_dash_lines(lines: list[str]) -> list[int]:
    """Return the line numbers that contain an em dash."""
    return [number for number, line in enumerate(lines, 1) if EM_DASH.search(line)]


def check(path: Path) -> list[str]:
    """Return one violation per em dash in a documentation file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        f"{path.relative_to(ROOT)}:{number}: em dash"
        for number in em_dash_lines(lines)
    ]


def main() -> int:
    """Check every documentation file and report all violations."""
    errors = [error for path in doc_files() for error in check(path)]
    if errors:
        print("\n".join(errors))
        return 1
    print(f"No em dashes in {len(doc_files())} Markdown files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

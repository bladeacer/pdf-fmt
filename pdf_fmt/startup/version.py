"""Version resolution for the CLI."""

import importlib.metadata
import os
import re


def get_script_version() -> str:
    """Resolves the version from CI, package metadata or pyproject.toml."""
    ci_version = os.environ.get('PDF_FMT_VERSION')
    if ci_version:
        return ci_version

    try:
        return importlib.metadata.version("pdf-fmt")
    except importlib.metadata.PackageNotFoundError:
        pass

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        toml_path = os.path.join(base_dir, "..", "..", "pyproject.toml")
        if os.path.exists(toml_path):
            with open(toml_path, 'r', encoding='utf-8') as f:
                match = re.search(r'version\s*=\s*"([^"]+)"', f.read())
                if match:
                    return match.group(1)
    except Exception:
        pass

    return "0.1.0"


SCRIPT_VERSION = get_script_version()

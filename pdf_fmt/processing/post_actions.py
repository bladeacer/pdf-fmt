import os
from typing import Any, Dict

PYPERCLIP_WARN = "Warning: 'pyperclip' library not found. Clipboard functionality disabled."


def copy_content(content: str) -> None:
    """Copies content to the clipboard with pyperclip when available."""
    try:
        import pyperclip
    except ImportError:
        print(PYPERCLIP_WARN)
        return

    try:
        pyperclip.copy(content)
        print("SUCCESS: Extracted content copied to clipboard.")
    except Exception as e:
        print(f"Warning: Could not copy to clipboard. Error: {e}")


def write_content_to_file(content: str, file_path: str) -> None:
    """Writes content to a UTF-8 text file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as target:
            target.write(content)
        print(f"SUCCESS: Extracted content written to '{file_path}'.")
    except Exception as e:
        print(f"Error: Could not write content to file '{file_path}'. {e}")


def perform_post_actions(content: str, config: Dict[str, Any]) -> None:
    """Copies content and writes it to the configured file path."""
    actions = config.get("actions", {})
    if actions.get("copy", True):
        copy_content(content)

    file_path = actions.get("write_file")
    if file_path and isinstance(file_path, str):
        resolved_path = os.path.abspath(os.path.expanduser(file_path))
        write_content_to_file(content, resolved_path)

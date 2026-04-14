from typing import Dict, Any, List, NamedTuple
import os
import re
from pdf_fmt.formatting import clean_and_lint_text

PYPERCLIP_WARN = "Warning: 'pyperclip' library not found. Clipboard functionality disabled."


def copy_content(content: str) -> None:
    """
    Copies content to clipboard using pyperclip.
    Checks for library availability at runtime.
    """
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


def write_content_to_file(content: str, file_path: str):
    """Writes content to a specified text file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"SUCCESS: Extracted content written to '{file_path}'.")
    except Exception as e:
        print(f"Error: Could not write content to file '{file_path}'. {e}")


def perform_post_actions(content: str, config: Dict[str, Any]):
    """Executes post-extraction actions (copy, write file)."""
    actions = config.get("actions", {})
    if actions.get("copy", True):
        copy_content(content)

    file_path = actions.get("write_file")
    if file_path and isinstance(file_path, str):
        expanded_path = os.path.expanduser(file_path)
        resolved_path = os.path.abspath(expanded_path)
        write_content_to_file(content, resolved_path)


class PageProcessArgs(NamedTuple):
    page_num: int
    page_text: str
    config: Dict[str, Any]
    allowed_chars_regex: str
    footer_patterns: List[str]
    spelling_locale: str
    ignore_list: List[str]


def _process_page_text_block(args: PageProcessArgs) -> List[str]:
    """
    Processes a single page block. Re-creates filter functions locally
    for picklability in multiprocessing environments.
    """
    if not args.page_text.strip():
        return []

    from pdf_fmt.core import (
        split_fmt_line, compile_footer_patterns,
        ln_cont_factory, is_ft_factory, format_indented_line
    )

    fmt_cfg = args.config.get("formatting", {})
    min_chars = fmt_cfg.get("min_chars_per_line", 0)
    max_chars = fmt_cfg.get("max_chars_per_line", 80)
    enforce_cap = fmt_cfg.get("enforce_line_capitalization", False)
    page_sep_mode = fmt_cfg.get("page_separator", "--- PAGE SEPARATOR ---")

    allowed_pattern = re.compile(args.allowed_chars_regex)
    compiled_footers = compile_footer_patterns(args.footer_patterns)

    filter_content = ln_cont_factory(allowed_pattern)
    is_footer = is_ft_factory(compiled_footers)

    processed_content: List[str] = []
    if args.page_num > 0:
        separators = {
            "___": "___",
            "--- PAGE SEPARATOR ---": f"\n--- Page {args.page_num + 1} ---"
        }
        if (sep := separators.get(page_sep_mode)):
            processed_content.append(sep)

    valid_lines: List[str] = []
    for raw_line in args.page_text.splitlines():
        filtered = filter_content(raw_line)

        if not filtered or is_footer(filtered):
            continue

        cleaned = clean_and_lint_text(filtered, args.spelling_locale, args.ignore_list)
        formatted = format_indented_line(cleaned)

        if formatted.strip():
            valid_lines.append(formatted)

    line_buffer = ""

    def flush_buffer(buffer: str):
        if buffer:
            processed_content.extend(split_fmt_line(buffer, max_chars, enforce_cap))

    for line in valid_lines:
        stripped = line.strip()

        is_break_type = (
            stripped.startswith(('-', '*')) or
            re.search(r'[.?!]$', stripped) or
            len(stripped) >= min_chars
        )

        if is_break_type:
            flush_buffer(line_buffer)
            line_buffer = line
        else:
            sep = "" if line_buffer.endswith('-') else " "
            line_buffer = (line_buffer + sep + stripped) if line_buffer else stripped

    flush_buffer(line_buffer)

    return processed_content

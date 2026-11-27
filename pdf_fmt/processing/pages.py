import re
from typing import Any, Dict, List, NamedTuple

from pdf_fmt.core import (
    compile_footer_patterns,
    format_indented_line,
    is_ft_factory,
    ln_cont_factory,
    split_fmt_line,
)
from pdf_fmt.formatting import clean_and_lint_text, replace_unicode_chars


class PageProcessArgs(NamedTuple):
    """One page block and the settings needed to process it."""

    page_num: int
    page_text: str
    config: Dict[str, Any]
    allowed_chars_regex: str
    footer_patterns: List[str]
    spelling_locale: str
    ignore_list: List[str]
    total_pages: int
    apply_variant: bool = True


def _get_separator(page_num: int, mode: str) -> str:
    """Returns the formatted page separator based on config."""
    if page_num <= 0:
        return ""
    separators = {
        "___": "\n\n___\n\n",
        "--- PAGE SEPARATOR ---": f"\n\n--- Page {page_num + 1} ---\n\n"
    }
    return separators.get(mode, "")


def _update_line_buffer(buffer: str, line: str) -> str:
    """Joins a line to the buffer, unless the buffer ends in a hyphen."""
    if not buffer:
        return line
    sep = "" if buffer.endswith('-') else " "
    return f"{buffer}{sep}{line.strip()}"


def _process_page_text_block(args: PageProcessArgs) -> List[str]:
    """Filters, wraps and lints the lines of one page block."""
    if not args.page_text.strip():
        return []

    cfg = args.config.get("formatting", {})
    max_chars = cfg.get("max_chars_per_line", 0)
    enforce_cap = cfg.get("enforce_line_capitalization", False)

    filter_content = ln_cont_factory(re.compile(args.allowed_chars_regex))
    is_footer = is_ft_factory(compile_footer_patterns(args.footer_patterns))

    processed_content: List[str] = []
    line_buffer = ""
    in_table = False

    def flush_buffer(buf: str) -> None:
        if buf:
            processed_content.extend(split_fmt_line(
                buf, max_chars, enforce_cap, args.spelling_locale
            ))

    for raw_line in args.page_text.splitlines():
        filtered = filter_content(replace_unicode_chars(raw_line))
        if not filtered or is_footer(filtered):
            continue

        cleaned = clean_and_lint_text(
            filtered, args.spelling_locale, args.ignore_list, args.apply_variant
        )
        trimmed = cleaned.strip()
        is_table = trimmed.startswith('|') and trimmed.endswith('|')

        if is_table:
            if not in_table:
                flush_buffer(line_buffer)
                line_buffer = ""
                processed_content.append("")
                in_table = True
            processed_content.append(trimmed)
            continue
        elif in_table:
            processed_content.append("")
            in_table = False

        formatted = format_indented_line(cleaned)
        if not formatted.strip():
            continue

        is_break = (
            trimmed.startswith(('-', '*'))
            or re.search(r'[.?!]$', trimmed)
            or len(trimmed) >= cfg.get("min_chars_per_line", 0)
        )
        if is_break:
            flush_buffer(line_buffer)
            line_buffer = formatted
        else:
            line_buffer = _update_line_buffer(line_buffer, formatted)

    flush_buffer(line_buffer)

    if (args.page_num + 1) < args.total_pages:
        separator = _get_separator(args.page_num, cfg.get("page_separator"))
        if separator:
            processed_content.append(separator)

    return processed_content

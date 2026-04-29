from typing import Dict, Any, List, NamedTuple, Tuple, Optional
import os
import re
import multiprocessing
import pdfplumber

from pdf_fmt.formatting import fix_spacing

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


def _get_page_elements(page, table_config: Dict[str, Any]) -> List[Tuple[float, str]]:
    tables = page.find_tables(table_settings=table_config)
    # Get bboxes and expand them by a tiny margin to catch "ghost" text
    table_bboxes = [t.bbox for t in tables]

    def is_outside_tables(obj):
        x0, top = obj.get("x0"), obj.get("top"),
        x1, bottom = obj.get("x1"), obj.get("bottom")
        if None in (x0, top, x1, bottom):
            return True

        for b in table_bboxes:
            # If any part of the text char is within 2pts of a table, filter it
            if not (
                x1 < b[0]-2 or x0 > b[2]+2
                or bottom < b[1]-2 or top > b[3]+2
            ):
                return False
        return True

    elements: List[Tuple[float, str]] = []
    for table in tables:
        raw = table.extract()
        if raw:
            # We wrap the table in a unique marker to prevent the text
            # processor from thinking it's just a normal line
            elements.append((table.bbox[1], _to_markdown_table(raw)))

    clean_page = page.filter(is_outside_tables)
    text = clean_page.extract_text(x_tolerance=2, y_tolerance=2)
    text = fix_spacing(text)

    if text:
        elements.append((0, text))

    elements.sort(key=lambda x: x[0])
    return elements


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
    """Handles the concatenation logic for the line buffer."""
    if not buffer:
        return line
    sep = "" if buffer.endswith('-') else " "
    return f"{buffer}{sep}{line.strip()}"


def _process_page_text_block(args: PageProcessArgs) -> List[str]:
    """Processes a single page block with reduced complexity."""
    if not args.page_text.strip():
        return []

    from pdf_fmt.core import (
        split_fmt_line, compile_footer_patterns, ln_cont_factory,
        is_ft_factory, format_indented_line
    )
    from pdf_fmt.formatting import clean_and_lint_text

    cfg = args.config.get("formatting", {})
    max_chars = cfg.get("max_chars_per_line", 0)
    enforce_cap = cfg.get("enforce_line_capitalization", False)

    filter_content = ln_cont_factory(re.compile(args.allowed_chars_regex))
    is_footer = is_ft_factory(compile_footer_patterns(args.footer_patterns))

    processed_content: List[str] = []
    line_buffer = ""
    in_table = False

    def flush_buffer(buf: str):
        if buf:
            processed_content.extend(split_fmt_line(
                buf, max_chars, enforce_cap
            ))

    for raw_line in args.page_text.splitlines():
        filtered = filter_content(raw_line)
        if not filtered or is_footer(filtered):
            continue

        cleaned = clean_and_lint_text(
            filtered, args.spelling_locale, args.ignore_list
        )
        trimmed = cleaned.strip()
        is_table = trimmed.startswith('|') and trimmed.endswith('|')

        # Table State Handling
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

        # Text Wrapping Logic
        formatted = format_indented_line(cleaned)
        if not formatted.strip():
            continue

        is_break = (trimmed.startswith(('-', '*')) or
                    re.search(r'[.?!]$', trimmed) or
                    len(trimmed) >= cfg.get("min_chars_per_line", 0))

        if is_break:
            flush_buffer(line_buffer)
            line_buffer = formatted
        else:
            line_buffer = _update_line_buffer(line_buffer, formatted)

    flush_buffer(line_buffer)

    if (sep := _get_separator(args.page_num, cfg.get("page_separator"))):
        processed_content.append(sep)

    return processed_content


def _to_markdown_table(table: List[List[Optional[str]]]) -> str:
    """Converts a table but avoids printing empty/broken Markdown structures."""
    if not table or len(table) < 1:
        return ""

    clean_table = [
        [" " if c is None else c.replace("\n", " ").strip() for c in row]
        for row in table if any(c is not None for c in row)
    ]

    if len(clean_table) < 2 or not any(clean_table[0]):
        return "\n" + "\n".join(" ".join(row) for row in clean_table) + "\n"

    headers = clean_table[0]
    col_count = len(headers)

    lines = [
        f"| {' | '.join(headers)} |",
        f"| {' | '.join(['---'] * col_count)} |"
    ]

    for row in clean_table[1:]:
        # Standardize row length to header length
        row = row[:col_count] + [""] * (col_count - len(row))
        lines.append(f"| {' | '.join(row)} |")

    return "\n" + "\n".join(lines) + "\n"


def _run_processing_pool(args_list: List[Any], cores: int) -> List[str]:
    """Handles the switch between parallel and sequential execution."""
    if len(args_list) > 1 and cores > 1:
        try:
            with multiprocessing.Pool(processes=cores) as pool:
                return [line for page_result in pool.map(
                    _process_page_text_block, args_list
                )
                        for line in page_result]
        except Exception as e:
            print(f"Warning: Multiprocessing failed ({e}). Falling back to sequential.")

    return [line for args in args_list
            for line in _process_page_text_block(args)]


def extract_text_from_pdf(
    pdf_path: str,
    config: Dict[str, Any],
    allowed_chars_regex_string: str,
    footer_regex_patterns: List[str],
    spelling_locale: str,
    ignore_list: List[str]
) -> Tuple[Optional[str], Optional[str]]:

    if not os.path.exists(pdf_path):
        return None, f"Error: PDF file not found at '{pdf_path}'"

    from pdf_fmt.core import post_process_content

    fmt_cfg = config.get("formatting", {})
    proc_cfg = config.get("processing", {})
    table_cfg = fmt_cfg.get("extract_table", {})

    max_cores = max(1, os.cpu_count() - 1)
    cores_used = int(proc_cfg.get("cores", max_cores))

    page_data_blocks: List[str] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                elements = _get_page_elements(page, table_cfg)
                page_data_blocks.append(
                    "\n\n".join(content for _, content in elements)
                )
    except Exception as e:
        return None, f"An error occurred during PDF parsing: {e}"

    pool_args = [
        PageProcessArgs(
            page_num=i,
            page_text=block,
            config=config,
            allowed_chars_regex=allowed_chars_regex_string,
            footer_patterns=footer_regex_patterns,
            spelling_locale=spelling_locale,
            ignore_list=ignore_list
        )
        for i, block in enumerate(page_data_blocks)
    ]

    extracted_lines = _run_processing_pool(pool_args, cores_used)

    return post_process_content(extracted_lines, config), None

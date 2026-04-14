from typing import Dict, Any, List, NamedTuple, Tuple, Optional
import os
import re
import multiprocessing
import pdfplumber

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
    from pdf_fmt.formatting import clean_and_lint_text

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


def _to_markdown_table(table: List[List[Optional[str]]]) -> str:
    """Converts a list-of-lists table into a GitHub-flavored Markdown table."""
    if not table or not any(table):
        return ""

    # Clean None values and newlines
    clean_table = [
        [" " if cell is None else cell.replace("\n", " ").strip() for cell in row]
        for row in table
    ]

    headers = clean_table[0]
    rows = clean_table[1:]

    markdown = f"| {' | '.join(headers)} |\n"
    markdown += f"| {' | '.join(['---'] * len(headers))} |\n"

    for row in rows:
        # Pad row if it's shorter than headers
        if len(row) < len(headers):
            row.extend([""] * (len(headers) - len(row)))
        markdown += f"| {' | '.join(row)} |\n"

    return markdown + "\n"


def _get_page_elements(page, table_config: Dict[str, Any]) -> List[Tuple[float, str]]:
    """Extracts and sorts tables and text for a single page."""
    tables = page.find_tables(table_settings=table_config)

    def is_outside_tables(obj):
        t_top, t_bottom = obj.get("top"), obj.get("bottom")
        if t_top is None or t_bottom is None:
            return True
        return not any(t.bbox[1] <= t_top and t_bottom <= t_bottom for t in tables)

    elements: List[Tuple[float, str]] = []

    for table in tables:
        raw = table.extract()
        if raw:
            elements.append((table.bbox[1], _to_markdown_table(raw)))

    clean_page = page.filter(is_outside_tables)
    text = clean_page.extract_text(layout=True, use_text_flow=True)
    if text:
        elements.append((0, text))

    elements.sort(key=lambda x: x[0])
    return elements


def _run_processing_pool(args_list: List[Any], cores: int) -> List[str]:
    """Handles the switch between parallel and sequential execution."""
    if len(args_list) > 1 and cores > 1:
        try:
            with multiprocessing.Pool(processes=cores) as pool:
                return [line for page_result in pool.map(_process_page_text_block, args_list) 
                        for line in page_result]
        except Exception as e:
            print(f"Warning: Multiprocessing failed ({e}). Falling back to sequential.")

    return [line for args in args_list for line in _process_page_text_block(args)]


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
                page_data_blocks.append("\n\n".join(content for _, content in elements))
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

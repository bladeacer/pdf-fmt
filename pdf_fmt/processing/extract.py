import os
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

from pdf_fmt.core import post_process_content
from pdf_fmt.spell.locale import (
    auto_apply_categories,
    auto_locale,
    locale_dictionary,
    script_detection_enabled,
)

from .pages import PageProcessArgs
from .pool import _run_processing_pool
from .tables import _get_page_elements


def extract_text_from_pdf(
    pdf_path: str,
    config: Dict[str, Any],
    allowed_chars_regex_string: str,
    footer_regex_patterns: List[str],
    spelling_locale: str,
    ignore_list: List[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Extracts and formats all pages of a PDF as text."""
    if not os.path.exists(pdf_path):
        return None, f"Error: PDF file not found at '{pdf_path}'"

    fmt_cfg = config.get("formatting", {})
    proc_cfg = config.get("processing", {})
    table_cfg = fmt_cfg.get("extract_table", {})

    max_cores = max(1, (os.cpu_count() or 2) - 1)
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

    script_enabled = script_detection_enabled(config)
    apply_variant = auto_apply_categories(config)['variant']
    pool_args: List[PageProcessArgs] = []
    for index, block in enumerate(page_data_blocks):
        block_locale = auto_locale(spelling_locale, block, script_enabled)
        ignores = (
            locale_dictionary(config, block_locale)
            if block_locale != spelling_locale else ignore_list
        )
        pool_args.append(PageProcessArgs(
            page_num=index,
            page_text=block,
            config=config,
            allowed_chars_regex=allowed_chars_regex_string,
            footer_patterns=footer_regex_patterns,
            spelling_locale=block_locale,
            ignore_list=ignores,
            total_pages=len(page_data_blocks),
            apply_variant=apply_variant,
        ))

    extracted_lines = _run_processing_pool(pool_args, cores_used)
    return post_process_content(extracted_lines, config), None

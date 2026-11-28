"""Pipeline coordination."""

import os
import sys
from typing import Any, Dict

from pdf_fmt.conversion import convert_to_pdf
from pdf_fmt.core import DEFAULT_CHARS_REGEX, DEFAULT_CONVERT_FORMATS
from pdf_fmt.processing import extract_text_from_pdf, perform_post_actions
from pdf_fmt.spell import locale_checks
from pdf_fmt.startup import setup_cli

from .cores import _get_validated_cores
from .images import _get_image_formats, _run_image_pipeline

__all__ = [
    "_get_image_formats",
    "_get_validated_cores",
    "_run_image_pipeline",
    "execute_main_pipeline",
]


def execute_main_pipeline(config: Dict[str, Any]) -> None:
    """Coordinates conversion, extraction, image handling and output actions."""
    args = setup_cli()

    locale, ignores = locale_checks(config)

    conv_cfg = config.get("conversion", {})
    formats = conv_cfg.get("supported_formats", DEFAULT_CONVERT_FORMATS)
    pdf_path, is_temp = convert_to_pdf(args.file_path, formats)

    if not pdf_path:
        sys.exit(1)

    filt_cfg = config.get("filters", {})
    footers = filt_cfg.get("footer_regexes", [])
    if not isinstance(footers, list):
        footers = []

    chars = filt_cfg.get("allowed_chars_regex", DEFAULT_CHARS_REGEX)
    if not isinstance(chars, str):
        chars = DEFAULT_CHARS_REGEX

    content, error = extract_text_from_pdf(
        pdf_path, config, chars, footers, locale, ignores
    )

    _run_image_pipeline(pdf_path, config.get("actions", {}), _get_validated_cores(config))

    if is_temp and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
            print(f"INFO: Cleaned up temporary PDF: {pdf_path}")
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")

    if error:
        print(f"Error: Extraction failed.\nDetails: {error}")
        sys.exit(1)

    if content:
        print(content)
        perform_post_actions(content, config)

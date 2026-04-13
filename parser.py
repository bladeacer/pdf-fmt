import sys
import os
import re
import subprocess
import io
import multiprocessing
import glob

from typing import Dict, Any, Callable, Optional

import pdf2image

from pdf_fmt.startup import setup_cli, IS_CI_BUILD
from pdf_fmt.core import NON_ALPHA_PATTERN, DEFAULT_CONVERT_FORMATS, DEFAULT_CHARS_REGEX
from pdf_fmt.core import (
    compile_footer_patterns, filter_line_content_factory,
    format_indented_line, is_footer_factory, write_content_to_file
)
from pdf_fmt.spell import locale_checks

# from pdfminer.pdfpage import PDFPage
# from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
# from pdfminer.converter import TextConverter
# from pdfminer.layout import LAParams

pyperclip = None
_CONVERSION_TOOL_CACHE: Optional[str] = None
FALLBACK_FORMAT = "JPEG"
# PDFMINER_IMG_REGEX = re.compile(r'(.+?)-p(\d+)-\d+\.')


def execute_main_pipeline(CONFIG: Dict[str, Any]) -> None:
    """
    Executes the main pipeline: CLI setup, dependency imports, config loading,
    filter compilation, conversion, extraction, cleanup, and post-actions.
    """
    args = setup_cli()
    input_file_path = args.file_path
    spelling_locale, ignore_list = locale_checks(CONFIG)

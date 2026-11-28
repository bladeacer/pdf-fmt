"""Small text, line and regex helpers."""

from .patterns import (
    DEFAULT_CHARS_REGEX,
    DEFAULT_CONVERT_FORMATS,
    NON_ALPHA_PATTERN,
    apply_regex_enclosure,
    compile_footer_patterns,
    is_ft_factory,
    ln_cont_factory,
)
from .text import (
    NBSP,
    enforce_capitalization,
    format_indented_line,
    post_process_content,
    preserve_case,
    replace_successive_spaces,
)
from .tokenisation import tokenize_text
from .wrapping import contains_cjk, split_fmt_line

__all__ = [
    "DEFAULT_CHARS_REGEX",
    "DEFAULT_CONVERT_FORMATS",
    "NBSP",
    "NON_ALPHA_PATTERN",
    "apply_regex_enclosure",
    "compile_footer_patterns",
    "contains_cjk",
    "enforce_capitalization",
    "format_indented_line",
    "is_ft_factory",
    "ln_cont_factory",
    "post_process_content",
    "preserve_case",
    "replace_successive_spaces",
    "split_fmt_line",
    "tokenize_text",
]

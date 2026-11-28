"""Text casing, spacing and enclosure helpers."""

import re
from typing import Any, Dict, List

from .patterns import apply_regex_enclosure

NBSP = '\u00A0'


def replace_successive_spaces(text: str) -> str:
    """Replaces multiple spaces with a single space."""
    return re.sub(r'\s{2,}', ' ', text).strip()


def preserve_case(original_word: str, translated_word: str, locale: str = '') -> str:
    """Applies original casing (UPPER, Title) to the translated word."""
    if not original_word or not translated_word:
        return translated_word

    if locale.lower().startswith('zh'):
        return translated_word

    if original_word.isupper():
        return translated_word.upper()

    if original_word[0].isupper():
        return translated_word.capitalize()

    return translated_word


def enforce_capitalization(line: str, locale: str = '') -> str:
    """Ensures the first alphabetic character of a Latin line is capitalized."""
    if locale.lower().startswith('zh'):
        return line

    stripped_line = line.lstrip()
    if not stripped_line:
        return line

    first_char = stripped_line[0]
    is_capitalise = (first_char.isalpha()
                     and not first_char.isupper()
                     and not stripped_line.startswith("http"))

    if is_capitalise:
        leading_ws = line[:len(line) - len(stripped_line)]
        return leading_ws + first_char.upper() + stripped_line[1:]

    return line


def post_process_content(lines: List[str], config: Dict[str, Any]) -> str:
    """Applies regex enclosures to the combined content."""
    processed_lines: List[str] = []
    enclosure_skip_warn: str = """
    Warning: 'regex_enclosures' in config is not a list.
    Skipping enclosure processing.
"""
    enclosure_configs = config.get(
        "formatting", {}
    ).get("regex_enclosures", [])

    if not isinstance(enclosure_configs, list):
        print(enclosure_skip_warn)
        enclosure_configs = []

    for line in lines:
        temp_line = line

        for item in enclosure_configs:
            enclosure_pattern = item.get("pattern")
            enclosure_wrapper = item.get("wrapper")

            if enclosure_pattern and enclosure_wrapper:
                temp_line = apply_regex_enclosure(temp_line,
                                                  enclosure_pattern,
                                                  enclosure_wrapper)

        processed_lines.append(temp_line)

    return "\n".join(processed_lines)


def format_indented_line(line: str) -> str:
    """Converts single-space indentation to a Markdown list item."""
    normalized_line = line.replace(NBSP, ' ')
    if normalized_line.startswith(' '):
        if not normalized_line.startswith('  '):
            if not re.match(r'^\s*[-*]', normalized_line.lstrip()):
                return "- " + normalized_line[1:]
    return normalized_line

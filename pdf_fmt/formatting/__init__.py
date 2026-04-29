from typing import List
from pdf_fmt.spell import enforce_spelling
from pdf_fmt.core import replace_successive_spaces
import re


def fix_spacing(text: str) -> str:
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    return text


def replace_unicode_chars(line: str) -> str:
    replacement_map = {
        "\u2013": "-",
        "\u2014": " -",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u00a0": " ",
    }

    table = str.maketrans(replacement_map)

    return line.translate(table)


def clean_and_lint_text(text: str, locale: str, ignore_list: List[str]) -> str:
    """Applies spelling linting and then cleans up spacing."""

    if locale.lower() in ["en-us", "en-uk"]:
        text = enforce_spelling(text, locale, ignore_list)
    text = replace_successive_spaces(text)
    text = fix_spacing(text)
    return text

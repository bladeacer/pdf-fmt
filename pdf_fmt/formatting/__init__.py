from typing import List
from pdf_fmt.spell import enforce_spelling
from pdf_fmt.core import replace_successive_spaces


def clean_and_lint_text(text: str, locale: str, ignore_list: List[str]) -> str:
    """Applies spelling linting and then cleans up spacing."""

    if locale.lower() in ["en-us", "en-uk"]:
        text = enforce_spelling(text, locale, ignore_list)
    text = replace_successive_spaces(text)
    return text

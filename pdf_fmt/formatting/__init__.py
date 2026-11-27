from typing import List

from pdf_fmt.core import contains_cjk, replace_successive_spaces
from pdf_fmt.spell import enforce_spelling
from pdf_fmt.spell.chinese import convert_chinese


def add_cjk_spacing(text: str) -> str:
    """Inserts spaces at CJK and Latin or digit boundaries."""
    chars = list(text)
    result: List[str] = []
    for index, char in enumerate(chars):
        if index and not chars[index - 1].isspace() and not char.isspace():
            if contains_cjk(char) != contains_cjk(chars[index - 1]):
                if char.isalnum() or chars[index - 1].isalnum():
                    result.append(' ')
        result.append(char)
    return ''.join(result)


def fix_spacing(text: str, cjk_spacing: bool = False) -> str:
    """Splits lower-to-upper transitions and optionally spaces CJK text."""
    chars = list(text)
    result: List[str] = []
    for char in chars:
        if result and (result[-1].islower() or result[-1].isdigit()) and char.isupper():
            result.append(' ')
        result.append(char)
    spaced = ''.join(result)
    return add_cjk_spacing(spaced) if cjk_spacing else spaced


def replace_unicode_chars(line: str) -> str:
    replacement_map = {
        "\u2013": "-",
        "\u2014": " -",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2026": "...",
        "\u00a0": " ",
        "\u00bf": "?",
        "\u00d7": "\\cdot",
        "\u00f7": "/",
        "\u00b1": "\\pm",
        "\u2212": "-",
        "\u2217": "*",
        "\u2215": "/",
        "\u221a": "\\sqrt",
        "\u221e": "\\infty",
        "\u2248": "\\approx",
        "\u2260": "\\neq",
        "\u2264": "\\leq",
        "\u2265": "\\geq",

        "\u2200": "\\forall",
        "\u2203": "\\exists",
        "\u2208": "\\in",
        "\u2209": "\\notin",
        "\u2211": "\\sum",
        "\u2202": "\\partial",
        "\u2206": "\\delta",
        "\u2207": "\\nabla",
        "\u222b": "\\int",
        "\u2192": "\\rightarrow",
        "\u2190": "\\leftarrow",
        "\u21d2": "\\implies",
        "\u21d4": "\\Longleftrightarrow",

        "\u03b1": "\\alpha",
        "\u03b2": "\\beta",
        "\u03b3": "\\gamma",
        "\u03b4": "\\delta",
        "\u03b5": "\\epsilon",
        "\u03bc": "\\mu",
        "\u03c0": "\\pi",
        "\u03c3": "\\sigma",
        "\u03c4": "\\tau",
        "\u03c6": "phi",
        "\u03b8": "theta",
        "\u03a9": "Omega",

        "\u00b2": "[^2]",
        "\u00b3": "[^3]",
        "\u00b9": "[^1]",
        "\u2070": "[^0]",
        "\u2074": "[^4]",
        "\u2075": "[^5]",
        "\u2076": "[^6]",
        "\u2077": "[^7]",
        "\u2078": "[^8]",
        "\u2079": "[^9]",

        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
    }

    table = str.maketrans(replacement_map)

    return line.translate(table)


def clean_and_lint_text(
    text: str, locale: str, ignore_list: List[str], apply_variant: bool = True
) -> str:
    """Applies spelling linting and then cleans up spacing."""

    if locale.startswith(('en-US', 'en-GB')):
        text = enforce_spelling(text, locale, ignore_list, apply_variant)
    if locale.startswith('zh-'):
        text = convert_chinese(text, locale)
    text = replace_successive_spaces(text)
    text = fix_spacing(text, cjk_spacing=locale.startswith('zh-'))
    return text

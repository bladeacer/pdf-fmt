"""Chinese script conversion, with no word-level spellcheck."""

import zhconv

TARGETS = {"zh-cn": "zh-cn", "zh-hk": "zh-hk", "zh-tw": "zh-tw"}


def convert_chinese(text: str, locale: str) -> str:
    """Converts Han text to the regional variant for a zh locale."""
    target = TARGETS.get(locale.lower())
    if target is None:
        return text
    return zhconv.convert(text, target)

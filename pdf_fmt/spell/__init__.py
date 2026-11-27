"""Locale checks and spelling backends."""

import re
from typing import Any, Dict, List, Tuple

from pdf_fmt.core import NON_ALPHA_PATTERN, preserve_case

from .english import apply_curated_map
from .locale import locale_dictionary, normalize_locale

BREAME_ERROR = "Error: 'breame' library required for spelling. Run: pip install breame."


def enforce_spelling(
    text: str, locale: str, ignore_list: List[str], apply_variant: bool = True
) -> str:
    """Enforces the variant spelling for English locales and preserves case."""
    resolved = normalize_locale(locale)
    if not apply_variant or resolved not in ('en-US', 'en-GB'):
        return text

    try:
        from breame.spelling import get_american_spelling, get_british_spelling
    except ImportError as error:
        raise RuntimeError(BREAME_ERROR) from error

    ignore_set = {item.lower() for item in ignore_list}

    def process_word(word: str) -> str:
        clean_word = NON_ALPHA_PATTERN.sub('', word)
        if not clean_word:
            return word

        lookup = clean_word.lower()
        if lookup in ignore_set:
            return word

        curated = apply_curated_map(lookup, resolved)
        if curated != lookup:
            base_converted = curated
        else:
            try:
                if resolved == 'en-US':
                    base_converted = get_american_spelling(lookup)
                else:
                    base_converted = get_british_spelling(lookup)
            except ValueError:
                base_converted = lookup

        if base_converted == lookup:
            return word

        converted = preserve_case(clean_word, base_converted, resolved)
        return word.replace(clean_word, converted, 1)

    return "".join(
        token if token.isspace() else process_word(token)
        for token in re.findall(r'\s+|\S+', text)
    )


def locale_checks(config: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Returns the validated locale and its per-locale ignore list."""
    spelling = config.get('filters', {}).get('linting', {}).get('spelling', {})
    locale = normalize_locale(spelling.get('enforce_locale', 'en-US'))
    return locale, locale_dictionary(config, locale)

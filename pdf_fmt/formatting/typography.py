"""Locale-aware typography hooks."""


def apply_typography(text: str, locale: str = '') -> str:
    """Applies quote, dash and ellipsis conventions for a locale."""
    if locale.upper().startswith('EN-GB'):
        opening, closing = '\u2018', '\u2019'
    else:
        opening, closing = '\u201c', '\u201d'

    result = text.replace('...', '\u2026')
    if locale.upper() in ('EN-US', 'EN-GB'):
        result = result.replace('--', '\u2013')
    parts = result.split('"')
    if len(parts) > 1:
        rebuilt = parts[0]
        for index, part in enumerate(parts[1:]):
            rebuilt += (opening if index % 2 == 0 else closing) + part
        result = rebuilt
    return result

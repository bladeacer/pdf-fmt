"""Curated English spelling overrides for known upstream gaps."""

TO_BRITISH = {
    "localization": "localisation",
    "localize": "localise",
    "localized": "localised",
    "organize": "organise",
    "analyze": "analyse",
    "behavior": "behaviour",
}
TO_AMERICAN = {british: american for american, british in TO_BRITISH.items()}


def apply_curated_map(word: str, locale: str) -> str:
    """Returns the curated spelling for one lowercase word."""
    mapping = TO_AMERICAN if locale == 'en-US' else TO_BRITISH
    return mapping.get(word, word)

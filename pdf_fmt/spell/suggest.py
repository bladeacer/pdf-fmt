"""Optional typo suggestions backed by pyspellchecker."""

from typing import List


def suggest_typos(text: str, language: str = 'en') -> List[str]:
    """Returns suggestions for unknown words with an optional backend."""
    try:
        from spellchecker import SpellChecker
    except ImportError as error:
        raise RuntimeError(
            "Install pyspellchecker to use typo suggestions"
        ) from error

    spell = SpellChecker(language=language)
    words = [word for word in text.split() if word.isalpha()]
    return [
        f"{word}: {', '.join(sorted(spell.candidates(word) or []))}"
        for word in sorted(spell.unknown(words))
    ]

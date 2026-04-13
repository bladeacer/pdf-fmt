"""
Spelling and clipboard helper
"""

import re
from typing import List, Any, Tuple, Dict

# Constants
PYPERCLIP_WARN = "Warning: 'pyperclip' library not found. Clipboard functionality disabled."
BREAME_ERROR = "Error: 'breame' library required for spelling. Run: pip install breame."


def enforce_spelling(text: str, locale: str, ignore_list: List[str]) -> str:
    """
    Enforces US or UK spelling using the breame library, preserving case.
    Handles local imports for breame and core utilities.
    """

    try:
        from breame.spelling import get_american_spelling, get_british_spelling
    except ImportError:
        print(BREAME_ERROR)

    try:
        from pdf_fmt.core import NON_ALPHA_PATTERN, preserve_case
    except ImportError:
        # Fallback if pattern isn't available
        NON_ALPHA_PATTERN = re.compile(r'[^a-zA-Z]')

        def preserve_case(original: str, modified: str) -> str:
            if original.isupper():
                return modified.upper()
            if original[0].isupper():
                return modified.capitalize()
            return modified

    ignore_set = {s.lower() for s in ignore_list}
    locale_upper = locale.upper()

    def process_word(word: str) -> str:
        clean_word = NON_ALPHA_PATTERN.sub('', word)
        if not clean_word:
            return word

        word_to_lookup_lower = clean_word.lower()
        if word_to_lookup_lower in ignore_set:
            return word

        try:
            if locale_upper == "EN-US":
                base_converted = get_american_spelling(word_to_lookup_lower)
            elif locale_upper == "EN-UK":
                base_converted = get_british_spelling(word_to_lookup_lower)
            else:
                base_converted = word_to_lookup_lower
        except (ValueError, Exception):
            base_converted = word_to_lookup_lower

        # If no change was made, return original; otherwise preserve case
        if base_converted == word_to_lookup_lower:
            return word

        case_preserved_word = preserve_case(clean_word, base_converted)
        return word.replace(clean_word, case_preserved_word, 1)

    return " ".join(process_word(w) for w in text.split())


def copy_content(content: str) -> None:
    """
    Copies content to clipboard using pyperclip.
    Checks for library availability at runtime.
    """
    try:
        import pyperclip
    except ImportError:
        print(PYPERCLIP_WARN)
        return

    try:
        pyperclip.copy(content)
        print("SUCCESS: Extracted content copied to clipboard.")
    except Exception as e:
        print(f"Warning: Could not copy to clipboard. Error: {e}")


def locale_checks(CONFIG: Dict[str, Any]) -> Tuple[str, List[str]]:
    filters_config = CONFIG.get("filters", {})
    linting_config = filters_config.get("linting", {})
    spelling_config = linting_config.get("spelling", {})

    spelling_locale = spelling_config.get("enforce_locale", "en-US")
    if not isinstance(spelling_locale, str):
        print("Warning: 'enforce_locale' in config is not a string. Defaulting to 'en-US'.")
        spelling_locale = "en-US"

    ignore_list = spelling_config.get("ignore_locale_strings", [])
    if not isinstance(ignore_list, list):
        print("Warning: 'ignore_locale_strings' in config is not a list. Defaulting to empty.")
        ignore_list = []

    return spelling_locale, ignore_list

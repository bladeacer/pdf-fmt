"""
Spelling and clipboard helper
"""


import sys
from typing import Callable, List

from pdf_fmt.core import NON_ALPHA_PATTERN

pyperclip = None
get_american_spelling: Callable[[str], str] = lambda w: w
get_british_spelling: Callable[[str], str] = lambda w: w

pyperclip_warn_str: str = """Warning: 'pyperclip' library not found.
Clipboard functionality will be disabled."""


def _import_dependencies() -> List[Callable[str], str]:
    """
    Dynamically imports non-stdlib dependencies and sets
    module-level variables.
    """

    global pyperclip
    breame_warn_str: str = """Error: The 'breame' library is required for
    spelling enforcement.  Please run: pip install breame.
"""

    try:
        import pyperclip as pc
        pyperclip = pc
    except ImportError:
        print(pyperclip_warn_str)
        pyperclip = None

    try:
        from breame.spelling import (
            get_american_spelling as g_a,
            get_british_spelling as g_b
        )
        get_american_spelling = g_a
        get_british_spelling = g_b
    except ImportError:
        if not getattr(sys, 'frozen', False):
            print(breame_warn_str)
            sys.exit(1)

        def stub_american(word: str) -> str: return word
        def stub_british(word: str) -> str: return word
        get_american_spelling = stub_american
        get_british_spelling = stub_british

    return get_american_spelling, get_british_spelling


def enforce_spell(text: str, locale: str, ignore_list: List[str]) -> str:
    """Enforces US or UK spelling using the breame library, preserving case,
    while ignoring words specified in the ignore_list.
    """
    global get_american_spelling, get_british_spelling
    from core import preserve_case

    ignore_set = {s.lower() for s in ignore_list}

    def process_word(word: str) -> str:
        clean_word = NON_ALPHA_PATTERN.sub('', word)
        if not clean_word:
            return word

        word_to_lookup_lower = clean_word.lower()

        if word_to_lookup_lower in ignore_set:
            return word

        try:
            if locale.upper() == "EN-US":
                base_converted = get_american_spelling(word_to_lookup_lower)
            elif locale.upper() == "EN-UK":
                base_converted = get_british_spelling(word_to_lookup_lower)
            else:
                base_converted = clean_word
        except ValueError:
            base_converted = clean_word

        if base_converted == word_to_lookup_lower:
            final_word_base = clean_word
        else:
            final_word_base = base_converted

        case_preserved_word = preserve_case(clean_word, final_word_base)
        return word.replace(clean_word, case_preserved_word, 1)

    return " ".join(process_word(word) for word in text.split())


def copy_content(is_pyperclip: bool, content: str) -> None:
    """Copies content to clipboard."""

    if pyperclip is None:
        print(pyperclip_warn_str)
        return

    try:
        pyperclip.copy(content)
        print("SUCCESS: Extracted content copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"Warning: Could not copy to clipboard. Error: {e}")

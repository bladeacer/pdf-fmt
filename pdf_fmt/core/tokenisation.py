"""Unicode-aware tokenisation for text helpers."""

import re
from typing import List

TOKEN_PATTERN = re.compile(r'\s+|\S+')


def tokenize_text(text: str) -> List[str]:
    """Splits text into whitespace and non-whitespace tokens."""
    return TOKEN_PATTERN.findall(text)

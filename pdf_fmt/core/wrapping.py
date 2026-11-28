"""Unicode-aware line wrapping."""

import re
from typing import List

from .text import enforce_capitalization

CJK_RANGES = '\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af'
CJK_PATTERN = re.compile(f'[{CJK_RANGES}]')
CJK_CLOSERS = '，。！？、；：）》」』】”’'
CJK_OPENERS = '（《「『【“‘'


def contains_cjk(text: str) -> bool:
    """Reports whether the text contains a CJK character."""
    return CJK_PATTERN.search(text) is not None


def _cjk_break_point(line: str, point: int) -> int:
    """Keeps CJK punctuation with the text it belongs to."""
    if point < len(line) and line[point] in CJK_CLOSERS:
        point -= 1
    if point > 0 and line[point - 1] in CJK_OPENERS:
        point += 1
    return max(1, min(point, len(line) - 1))


def split_fmt_line(line: str, max_len: int, enforce_cap: bool, locale: str = '') -> List[str]:
    """Splits a line at a space or, for CJK text, at a character boundary."""
    pieces: List[str] = []

    if enforce_cap:
        line = enforce_capitalization(line, locale)

    cjk = contains_cjk(line)
    while len(line) > max_len and max_len > 0:
        break_point = line.rfind(' ', 0, max_len + 1)

        if break_point == -1 or break_point > len(line) * 0.75:
            break_point = max_len
        if cjk:
            break_point = _cjk_break_point(line, break_point)

        pieces.append(line[:break_point].strip())
        line = line[break_point:].strip()

    if line:
        pieces.append(line)

    return pieces

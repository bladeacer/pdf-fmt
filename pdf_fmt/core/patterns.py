"""Regex constants and filter factories."""

import re
from typing import Callable, List

DEFAULT_CHARS_REGEX = r"[\w\s!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~]+"
DEFAULT_CONVERT_FORMATS = ['pptx', 'ppt', 'doc', 'docx', 'odt']
NON_ALPHA_PATTERN = re.compile(r'[^\w]')


def compile_footer_patterns(patterns: List[str]) -> List[re.Pattern]:
    """Compiles list of regex strings into regex objects."""
    regex_list: List[re.Pattern] = []

    for pattern_string in patterns:
        try:
            regex_list.append(re.compile(pattern_string, re.IGNORECASE))
        except re.error as e:
            print(f"""Warning: Invalid regex pattern '{pattern_string}' skipped
Error: {e}
""")
    return regex_list


def apply_regex_enclosure(text: str, pattern: str, wrapper: str) -> str:
    """Wraps content matching a regex pattern with custom symbols."""
    if not pattern or not wrapper:
        return text

    try:
        compiled_pattern = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        print(f"""Warning: Invalid enclosure regex pattern '{pattern}' skipped
Error: {e}
""")
        return text

    def wrapper_func(match: re.Match) -> str:
        return f"{wrapper}{match.group(0)}{wrapper}"

    return compiled_pattern.sub(wrapper_func, text)


def ln_cont_factory(allowed_chars_pattern: re.Pattern) -> Callable[[str], str]:
    """Creates a line content filter function based on a regex pattern."""
    def filter_func(line: str) -> str:
        return " ".join(allowed_chars_pattern.findall(line)).strip()
    return filter_func


def is_ft_factory(comp_foot_pattns: List[re.Pattern]) -> Callable[[str], bool]:
    """Creates a footer checker function from a list of regex patterns."""
    def is_footer_func(line: str) -> bool:
        cleaned_line = line.strip()
        if not cleaned_line:
            return False
        for pattern in comp_foot_pattns:
            if pattern.match(cleaned_line):
                return True
        return False
    return is_footer_func

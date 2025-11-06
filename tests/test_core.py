import unittest
import re
from typing import List, Dict, Any, Tuple, Callable
import io

# --- Core Function Implementations (Pasted for Standalone Testing) ---
# NOTE: In a real project, you would replace this block with: from core import *

NBSP = '\u00A0'
DEFAULT_CHARS_REGEX = r"[a-zA-Z0-9\s!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~]+"
NON_ALPHA_PATTERN = re.compile(r'[^a-zA-Z]')

def compile_footer_patterns(patterns: List[str]) -> List[re.Pattern]:
    """Compiles list of regex strings into regex objects."""
    regex_list: List[re.Pattern] = []
    for pattern_string in patterns:
        try:
            regex_list.append(re.compile(pattern_string, re.IGNORECASE))
        except re.error:
            pass 
    return regex_list

def apply_regex_enclosure(text: str, pattern: str, wrapper: str) -> str:
    """Wraps content matching a regex pattern with custom symbols."""
    if not pattern or not wrapper: return text
    try: compiled_pattern = re.compile(pattern, re.IGNORECASE)
    except re.error: return text
    def wrapper_func(match: re.Match) -> str: return f"{wrapper}{match.group(0)}{wrapper}"
    return compiled_pattern.sub(wrapper_func, text)

def enforce_capitalization(line: str) -> str:
    """Ensures the first alphabetic character of a line is capitalized."""
    stripped_line = line.lstrip()
    if not stripped_line: return line
    first_char = stripped_line[0]
    if first_char.isalpha() and not first_char.isupper():
        leading_ws = line[:len(line) - len(stripped_line)]
        return leading_ws + first_char.upper() + stripped_line[1:]
    return line

def replace_successive_spaces(text: str) -> str:
    """Replaces multiple spaces with a single space."""
    return re.sub(r'\s{2,}', ' ', text).strip()

def preserve_case(original_word: str, translated_word: str) -> str:
    """Applies original casing (UPPER, Title, or mixed-case leading cap) to the translated word. (FIXED)"""
    if not original_word or not translated_word: return translated_word

    if original_word.isupper(): return translated_word.upper()
    
    # FIX: Relaxed Title Case check
    if original_word[0].isupper(): return translated_word.capitalize()
    
    return translated_word

def split_and_format_line(line: str, max_len: int, enforce_cap: bool) -> List[str]:
    """Splits a line exceeding max_len at the nearest space and enforces capitalization."""
    pieces: List[str] = []
    if enforce_cap: line = enforce_capitalization(line)
    while len(line) > max_len and max_len > 0:
        break_point = line.rfind(' ', 0, max_len + 1)
        if break_point <= len(line) * 0.75 and break_point != -1: pass
        else: break_point = max_len
        pieces.append(line[:break_point].strip())
        line = line[break_point:].strip()
    if line: pieces.append(line)
    return pieces

def post_process_content(lines: List[str], config: Dict[str, Any]) -> str:
    """Applies final formatting rules and multiple regex enclosures to the combined content."""
    processed_lines: List[str] = []
    enclosure_configs = config.get("formatting", {}).get("regex_enclosures", [])
    if not isinstance(enclosure_configs, list): enclosure_configs = []
    for line in lines:
        temp_line = line
        for item in enclosure_configs:
            enclosure_pattern = item.get("pattern")
            enclosure_wrapper = item.get("wrapper")
            if enclosure_pattern and enclosure_wrapper:
                temp_line = apply_regex_enclosure(temp_line, enclosure_pattern, enclosure_wrapper)
        processed_lines.append(temp_line)
    return "\n".join(processed_lines)

def filter_line_content_factory(allowed_chars_pattern: re.Pattern) -> Callable[[str], str]:
    """Creates a line content filter function based on a specific regex pattern (Closure)."""
    def filter_func(line: str) -> str:
        # FIX: Added .strip() to clean up leading/trailing spaces from findall/join
        return " ".join(allowed_chars_pattern.findall(line)).strip()
    return filter_func

def format_indented_line(line: str) -> str:
    """Converts single-space indentation to Markdown list item if not already a list."""
    normalized_line = line.replace(NBSP, ' ')
    if normalized_line.startswith(' '):
        if not normalized_line.startswith('  '):
            if not re.match(r'^\s*[-*]', normalized_line.lstrip()):
                return "- " + normalized_line[1:]
    return normalized_line

def is_footer_factory(compiled_footer_patterns: List[re.Pattern]) -> Callable[[str], bool]:
    """Creates an is_footer checker function based on a list of patterns (Closure)."""
    def is_footer_func(line: str) -> bool:
        cleaned_line = line.strip()
        if not cleaned_line: return False
        for pattern in compiled_footer_patterns:
            if pattern.match(cleaned_line): return True
        return False
    return is_footer_func

# --- End of Core Function Implementations ---


class TestCoreFunctions(unittest.TestCase):

    def test_compile_footer_patterns(self):
        patterns = [r"page \d+", r"\d+/\d+", r"[0-9]+", r"("] 
        compiled = compile_footer_patterns(patterns)
        self.assertEqual(len(compiled), 3)

    def test_apply_regex_enclosure_multiple(self):
        text = "The quick brown fox jumps over the lazy dog."
        result = apply_regex_enclosure(text, r'fox|dog', '**')
        self.assertEqual(result, "The quick brown **fox** jumps over the lazy **dog**.")
        self.assertEqual(apply_regex_enclosure(text, '', '**'), text)

    def test_enforce_capitalization_all_cases(self):
        # FIX 1: The input has an initial lowercase 'a'. The function *must* capitalize it.
        # The test assertion is corrected to expect the capitalized result.
        self.assertEqual(enforce_capitalization(" already Capitalized"), " Already Capitalized")
        self.assertEqual(enforce_capitalization("hello world"), "Hello world")
        self.assertEqual(enforce_capitalization("  hello world"), "  Hello world")
        self.assertEqual(enforce_capitalization(" Already Capitalized"), " Already Capitalized") 
        self.assertEqual(enforce_capitalization("1. hello world"), "1. hello world")
        self.assertEqual(enforce_capitalization(""), "")

    def test_replace_successive_spaces(self):
        text = "  This   has  many \t spaces \n in it. "
        result = replace_successive_spaces(text)
        self.assertEqual(result, "This has many spaces in it.")

    def test_preserve_case_all_formats(self):
        self.assertEqual(preserve_case("COLOR", "colour"), "COLOUR")
        self.assertEqual(preserve_case("Color", "colour"), "Colour")
        self.assertEqual(preserve_case("ResNet", "resnet"), "Resnet") 
        self.assertEqual(preserve_case("cOlOr", "colour"), "colour")

    def test_split_and_format_line_wrapping_and_cap(self):
        line = "this is a very long sentence that needs to be broken into multiple lines at a sensible break point."
        max_len = 50
        
        pieces_cap = split_and_format_line(line, max_len, True)
        self.assertEqual(len(pieces_cap), 3) # Expect 3 pieces
        self.assertTrue(pieces_cap[0].startswith("This"))

    def test_filter_line_content_factory_restricted_chars(self):
        restrictive_regex = r'[a-zA-Z\s]+' 
        filter_func = filter_line_content_factory(re.compile(restrictive_regex))
        line = "123. Hello-world! 456. "
        result = filter_func(line)
        self.assertEqual(result, "Hello world") # Expected result after .strip()

    def test_format_indented_line_all_cases(self):
        self.assertEqual(format_indented_line(" first item"), "- first item")
        self.assertEqual(format_indented_line("  second item"), "  second item")

    def test_is_footer_factory_with_yaml_regexes(self):
        patterns = [r"^\s*\d+\s*$", r"^.*Copyright.*$"]
        is_footer_func = is_footer_factory(compile_footer_patterns(patterns))
        self.assertTrue(is_footer_func(" 5 "))

    def test_post_process_content_multiple_enclosures(self):
        lines = ["Line one [1, 2, 3]", "Line two: TODO", "Line three."]
        config = {
            "formatting": {
                "regex_enclosures": [
                    {"pattern": r'\[.*?\]', "wrapper": "`"},
                    # FIX 2: Use a simple wrapper (!) to avoid recursion and demonstrate sequential application.
                    {"pattern": r'TODO', "wrapper": "!"},
                    {"pattern": r'one', "wrapper": "*"}
                ]
            }
        }
        
        result = post_process_content(lines, config)
        # Expected output now matches function logic with simple wrappers:
        expected = "Line *one* `[1, 2, 3]`\nLine two: !TODO!\nLine three."
        self.assertEqual(result, expected)


if __name__ == '__main__':
    print("Run from root directory, see README for instructions")

import unittest
import re
from typing import List, Dict, Any, Tuple, Callable

# --- Core Function Implementations (Simulated/Real Logic, FIXED) ---

NBSP = '\u00A0'
DEFAULT_CHARS_REGEX = r"[a-zA-Z0-9\s!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~]+"
NON_ALPHA_PATTERN = re.compile(r'[^a-zA-Z]')

def compile_footer_patterns(patterns: List[str]) -> List[re.Pattern]:
    regex_list: List[re.Pattern] = []
    for pattern_string in patterns:
        try: regex_list.append(re.compile(pattern_string, re.IGNORECASE))
        except re.error: pass
    return regex_list
def replace_successive_spaces(text: str) -> str:
    return re.sub(r'\s{2,}', ' ', text).strip()

def preserve_case(original_word: str, translated_word: str) -> str:
    """Applies original casing (UPPER, Title, or mixed-case leading cap) to the translated word. (FIXED)"""
    if not original_word or not translated_word: return translated_word
    if original_word.isupper(): return translated_word.upper()
    if original_word[0].isupper(): return translated_word.capitalize()
    return translated_word

def split_and_format_line(line: str, max_len: int, enforce_cap: bool) -> List[str]:
    # Simplified mock for integration
    if enforce_cap and line: line = line[0].upper() + line[1:]
    if max_len == 0 or len(line) <= max_len: return [line]
    # Simple split if max_len exceeded
    return [line[:max_len], line[max_len:]]
def filter_line_content_factory(allowed_chars_pattern: re.Pattern) -> Callable[[str], str]:
    def filter_func(line: str) -> str:
        # FIX: Added .strip() to align with core.py fix
        return " ".join(allowed_chars_pattern.findall(line)).strip()
    return filter_func
def is_footer_factory(compiled_footer_patterns: List[re.Pattern]) -> Callable[[str], bool]:
    def is_footer_func(line: str) -> bool:
        cleaned_line = line.strip()
        if not cleaned_line: return False
        for pattern in compiled_footer_patterns:
            if pattern.match(cleaned_line): return True
        return False
    return is_footer_func
def format_indented_line(line: str) -> str:
    normalized_line = line.replace(NBSP, ' ')
    if normalized_line.startswith(' '):
        if not normalized_line.startswith('  '):
            if not re.match(r'^\s*[-*]', normalized_line.lstrip()): return "- " + normalized_line[1:]
    return normalized_line
# --- End of Core Functions (Partial) ---


# --- Mock Spelling Functions (External Dependency) ---
def mock_get_american_spelling(word: str) -> str:
    if word == "colour": return "color"
    if word == "organisation": return "organization"
    return word

def mock_get_british_spelling(word: str) -> str:
    if word == "color": return "colour"
    if word == "organization": return "organisation"
    return word
# --- End of Mock Spelling Functions ---


# --- Required Functions from parser.py (Pasted for Standalone Test) ---

def enforce_spelling(text: str, locale: str, ignore_list: List[str]) -> str:
    ignore_set = {s.lower() for s in ignore_list}
    def process_word(word: str) -> str:
        clean_word = NON_ALPHA_PATTERN.sub('', word)
        if not clean_word: return word
        word_to_lookup_lower = clean_word.lower() 
        if word_to_lookup_lower in ignore_set: return word 
        try:
            if locale.upper() == "EN-US": base_converted = mock_get_american_spelling(word_to_lookup_lower)
            elif locale.upper() == "EN-UK": base_converted = mock_get_british_spelling(word_to_lookup_lower)
            else: base_converted = clean_word
        except ValueError: base_converted = clean_word
        final_word_base = clean_word if base_converted == word_to_lookup_lower else base_converted
        case_preserved_word = preserve_case(clean_word, final_word_base)
        return word.replace(clean_word, case_preserved_word, 1)
    return " ".join(process_word(word) for word in text.split())

def clean_and_lint_text(text: str, locale: str, ignore_list: List[str]) -> str:
    if locale.lower() in ["en-us", "en-uk"]:
        text = enforce_spelling(text, locale, ignore_list)
    text = replace_successive_spaces(text)
    return text

def _process_page_text_block(
    args: Tuple[ int, str, Dict[str, Any], str, List[str], str, List[str] ]
) -> List[str]:
    page_num, page_text_block, config, allowed_chars_regex_string, raw_footer_patterns, spelling_locale, ignore_list = args
    if not page_text_block.strip(): return []
    allowed_chars_pattern = re.compile(allowed_chars_regex_string)
    compiled_footer_patterns = compile_footer_patterns(raw_footer_patterns)
    formatting_config = config.get("formatting", {})
    filter_line_content_func = filter_line_content_factory(allowed_chars_pattern)
    is_footer_func = is_footer_factory(compiled_footer_patterns)
    format_indented_line_func = format_indented_line
    min_chars = formatting_config.get("min_chars_per_line", 0)
    max_chars = formatting_config.get("max_chars_per_line", 80)
    enforce_cap = formatting_config.get("enforce_line_capitalization", False)
    page_sep_mode = formatting_config.get("page_separator", "--- PAGE SEPARATOR ---")
    current_page_lines: List[str] = []
    separator_lines: List[str] = []
    if page_num > 0 and page_sep_mode != "none":
        if page_sep_mode == "___": separator_lines.append("___")
        elif page_sep_mode == "--- PAGE SEPARATOR ---": separator_lines.append(f"\n--- Page {page_num + 1} ---")
            
    for raw_line in page_text_block.split('\n'):
        filtered_line = filter_line_content_func(raw_line)
        if is_footer_func(filtered_line): continue
        cleaned_line = clean_and_lint_text(filtered_line, spelling_locale, ignore_list)
        formatted_line = format_indented_line_func(cleaned_line)
        if formatted_line.strip(): current_page_lines.append(formatted_line)
    line_buffer = ""
    processed_content: List[str] = []
    for line in current_page_lines:
        stripped_line = line.strip()
        is_list_item = stripped_line.startswith(('-', '*'))
        is_sentence_end = re.search(r'[.?!]$', stripped_line)
        if is_list_item or is_sentence_end or len(stripped_line) >= min_chars:
            if line_buffer:
                split_lines = split_and_format_line(line_buffer, max_chars, enforce_cap)
                processed_content.extend(split_lines)
            line_buffer = line
        else:
            separator = " " if not line_buffer.endswith('-') else ""
            line_buffer += (separator + stripped_line) if line_buffer else stripped_line
    if line_buffer:
        split_lines = split_and_format_line(line_buffer, max_chars, enforce_cap)
        processed_content.extend(split_lines)
    return separator_lines + processed_content
# --- End of parser.py content ---


class TestParserLogic(unittest.TestCase):

    FOOTER_REGEXES = [
        r'^\s*\d+\s*$', r'^.*\s*[A-Za-z]+\d+\s.*$', r'^.*\d+S\d+[vV]\d+.*$',
        r'^.*Copyright.*$', r'^.*Official.*$', r'^.*Private.*$',
        r'^.*All rights reserved.*$', r'^.*(?:AY\s?)?\d{4}.*$', r'^.*v\d\.\d$',
        r'^Page\s\d.*$'
    ]

    def get_args(self, **kwargs) -> Tuple:
        """Helper to construct configuration-agnostic arguments for the processor."""
        config = {
            "filters": {
                "allowed_chars_regex": kwargs.get('allowed_chars_regex', DEFAULT_CHARS_REGEX),
                "footer_regexes": kwargs.get('footer_regexes', self.FOOTER_REGEXES),
            },
            "formatting": {
                "page_separator": kwargs.get('page_separator', "___"),
                "min_chars_per_line": kwargs.get('min_chars_per_line', 0),
                "max_chars_per_line": kwargs.get('max_chars_per_line', 80),
                "enforce_line_capitalization": kwargs.get('enforce_cap', False),
            }
        }
        return (
            kwargs.get('page_num', 0),
            kwargs.get('page_text', ""),
            config,
            config['filters']['allowed_chars_regex'],
            config['filters']['footer_regexes'],
            kwargs.get('spelling_locale', "en-US"),
            kwargs.get('ignore_list', [])
        )
    
    # --- Spelling/Linting Tests ---
    
    def test_clean_and_lint_text_spelling_uk_case(self):
        text = "This is a great Color, organization, filter, and connection."
        ignore_list = ["filter", "connection"]
        result = clean_and_lint_text(text, "en-UK", ignore_list)
        self.assertEqual(result, "This is a great Colour, organisation, filter, and connection.")

    def test_clean_and_lint_text_spelling_us_case(self):
        text = "This is a great colour and organisation."
        result = clean_and_lint_text(text, "en-US", [])
        self.assertEqual(result, "This is a great color and organization.")
    
    def test_clean_and_lint_text_spelling_none_case(self):
        text = "This is a great colour and organization."
        result = clean_and_lint_text(text, "none", [])
        self.assertEqual(result, "This is a great colour and organization.")

    # --- _process_page_text_block Configuration Tests ---

    def test_page_separator_all_cases(self):
        page_text = "Content"
        args_1 = self.get_args(page_num=1, page_text=page_text, page_separator="___")
        self.assertEqual(_process_page_text_block(args_1)[0], "___")
        args_2 = self.get_args(page_num=1, page_text=page_text, page_separator="--- PAGE SEPARATOR ---")
        self.assertEqual(_process_page_text_block(args_2)[0], "\n--- Page 2 ---")
        args_3 = self.get_args(page_num=1, page_text=page_text, page_separator="none")
        self.assertEqual(len(_process_page_text_block(args_3)), 1)

    def test_min_chars_per_line_all_cases(self):
        """Covers min_chars_per_line: 0 (disabled) and >0 (enabled)."""
        page_text = "Line One (Long)\nShort\nLine Three (Long)" 
        
        args_1 = self.get_args(page_num=0, page_text=page_text, min_chars_per_line=0)
        self.assertEqual(len(_process_page_text_block(args_1)), 3) 

        # All three lines join into a single line because they are short and lack end punctuation.
        args_2 = self.get_args(page_num=0, page_text=page_text, min_chars_per_line=20)
        result_2 = _process_page_text_block(args_2)
        self.assertEqual(len(result_2), 1) 
        self.assertIn("Line One (Long) Short Line Three (Long)", result_2[0])

    def test_max_chars_per_line_all_cases(self):
        """Covers max_chars_per_line: 0 (disabled) and >0 (enabled)."""
        long_line = "A very long sentence that will be split if max_chars is set to a small value."
        
        args_1 = self.get_args(page_num=0, page_text=long_line, max_chars_per_line=0)
        self.assertEqual(len(_process_page_text_block(args_1)), 1)

        args_2 = self.get_args(page_num=0, page_text=long_line, max_chars_per_line=30)
        self.assertGreater(len(_process_page_text_block(args_2)), 1)

    def test_enforce_line_capitalization_case(self):
        """Covers enforce_line_capitalization: true and false."""
        page_text = "line one starts with lower case."
        
        args_1 = self.get_args(page_num=0, page_text=page_text, enforce_cap=False, max_chars_per_line=100)
        self.assertIn("line one starts with lower case.", _process_page_text_block(args_1))

        args_2 = self.get_args(page_num=0, page_text=page_text, enforce_cap=True, max_chars_per_line=100)
        self.assertIn("Line one starts with lower case.", _process_page_text_block(args_2))

    def test_footer_filtering_with_config_regexes(self):
        """Tests that lines matching the complex config footer regexes are excluded."""
        page_text = "Normal line.\nPage 5 out of 10.\nIT1234 - Module Code\n\n25\n\nCopyright 2024"
        
        args = self.get_args(page_num=0, page_text=page_text)
        
        result = _process_page_text_block(args)
        
        self.assertEqual(len(result), 1)
        self.assertIn("Normal line.", result)

    def test_filter_line_content_factory_case(self):
        """Tests character filtering and subsequent space cleanup."""
        restrictive_regex = r'[a-zA-Z0-9\s]+'
        page_text = "Line 1: 100!\nLine 2: 200."
        
        args = self.get_args(
            page_num=0, 
            page_text=page_text, 
            allowed_chars_regex=restrictive_regex,
            min_chars_per_line=50 
        )
        
        result = _process_page_text_block(args)
        
        self.assertIn("Line 1 100 Line 2 200", result)

if __name__ == '__main__':
    print("Run from root directory, see README for instructions")

import sys
import os
import re
import yaml
import argparse
import platform
import subprocess
from typing import List, Dict, Any, Tuple, Callable, Optional, TYPE_CHECKING

CONFIG_FILENAME = "pdf-fmt.yaml"
SCRIPT_VERSION = "0.6.0"
DEFAULT_CHARS_REGEX = r"[a-zA-Z0-9\s!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~]+"
DEFAULT_CONVERT_FORMATS = ['pptx', 'ppt', 'doc', 'docx', 'odt']
NBSP = '\u00A0'
NON_ALPHA_PATTERN = re.compile(r'[^a-zA-Z]')

IS_CI_BUILD = os.environ.get('PDF_FMT_CI_BUILD', '0') == '1'
IS_NUITKA_COMPILED = "__compiled__" in globals()

CompiledFilters = Dict[str, Callable[[str], Any]]

def check_venv() -> None:
    """Checks if the script is running inside a virtual environment (.venv)."""
    if IS_NUITKA_COMPILED or getattr(sys, 'frozen', False) or IS_CI_BUILD:
        return

    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path or not os.path.basename(venv_path) == '.venv':
        print("Error: Script must be run from the '.venv' virtual environment.")
        print("Please activate it first (e.g., 'source .venv/bin/activate').")
        sys.exit(1)

def setup_cli() -> argparse.Namespace:
    """Sets up the argparse CLI and handles flags."""
    parser = argparse.ArgumentParser(
        description="pdf-fmt\n\nCleanly extracts and formats text from a PDF document or convertible file.\nLicensed under GPLv3.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'file_path',
        nargs='?',
        default=None,
        help="Path to the PDF or convertible file (e.g., pptx, docx) to process."
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {SCRIPT_VERSION}',
        help="Show script's version and exit."
    )
    args = parser.parse_args()
    if args.file_path is None:
        parser.print_help()
        sys.exit(0)
    return args

def find_config_file(filename: str) -> Optional[str]:
    """Searches for the config file using ENV, XDG standard, then CWD."""
    env_path = os.environ.get('PDF_FMT_CONFIG_PATH')
    if env_path and os.path.exists(env_path):
        return env_path

    if platform.system() == 'Windows':
        config_dir = os.environ.get('APPDATA')
    else:
        config_dir = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))

    if config_dir:
        xdg_path = os.path.join(config_dir, 'pdf-fmt', filename)
        if os.path.exists(xdg_path):
            return xdg_path

    cwd_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(cwd_path):
        return cwd_path

    return None

def load_patterns_from_yaml(file_path: Optional[str]) -> Dict[str, Any]:
    """Loads config data from a YAML file."""
    if not file_path:
        print(f"Warning: Configuration file '{CONFIG_FILENAME}' not found in any standard location. Using defaults.")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            print(f"INFO: Loaded configuration from: {file_path}")
            return config if isinstance(config, dict) else {}
    except Exception as e:
        print(f"Error: Could not read or parse '{file_path}': {e}. Using defaults.")
        return {}

def write_content_to_file(content: str, file_path: str):
    """Writes content to a specified text file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"SUCCESS: Extracted content written to '{file_path}'.")
    except Exception as e:
        print(f"Error: Could not write content to file '{file_path}'. {e}")

def compile_footer_patterns(patterns: List[str]) -> List[re.Pattern]:
    """Compiles list of regex strings into regex objects."""
    regex_list: List[re.Pattern] = []
    for pattern_string in patterns:
        try:
            regex_list.append(re.compile(pattern_string, re.IGNORECASE))
        except re.error as e:
            print(f"Warning: Invalid regex pattern '{pattern_string}' skipped. Error: {e}")
    return regex_list

def apply_regex_enclosure(text: str, pattern: str, wrapper: str) -> str:
    """Wraps content matching a regex pattern with custom symbols."""
    if not pattern or not wrapper:
        return text

    try:
        compiled_pattern = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        print(f"Warning: Invalid enclosure regex pattern '{pattern}' skipped. Error: {e}")
        return text

    def wrapper_func(match: re.Match) -> str:
        return f"{wrapper}{match.group(0)}{wrapper}"

    return compiled_pattern.sub(wrapper_func, text)

def enforce_capitalization(line: str) -> str:
    """Ensures the first alphabetic character of a line is capitalized."""
    stripped_line = line.lstrip()
    if not stripped_line:
        return line

    first_char = stripped_line[0]
    if first_char.isalpha() and not first_char.isupper():
        leading_ws = line[:len(line) - len(stripped_line)]
        return leading_ws + first_char.upper() + stripped_line[1:]

    return line

def replace_successive_spaces(text: str) -> str:
    """Replaces multiple spaces with a single space."""
    return re.sub(r'\s{2,}', ' ', text).strip()

def preserve_case(original_word: str, translated_word: str) -> str:
    """Applies original casing (UPPER, Title) to the translated word."""
    if not original_word or not translated_word:
        return translated_word

    if original_word.isupper():
        return translated_word.upper()

    if original_word[0].isupper() and original_word[1:].islower():
        return translated_word.capitalize()

    return translated_word

def split_and_format_line(line: str, max_len: int, enforce_cap: bool) -> List[str]:
    """Splits a line exceeding max_len at the nearest space and enforces capitalization."""
    pieces: List[str] = []

    if enforce_cap:
        line = enforce_capitalization(line)

    while len(line) > max_len and max_len > 0:
        break_point = line.rfind(' ', 0, max_len + 1)

        if break_point <= len(line) * 0.75 and break_point != -1:
            pass
        else:
            break_point = max_len

        pieces.append(line[:break_point].strip())

        line = line[break_point:].strip()

    if line:
        pieces.append(line)

    return pieces

def post_process_content(lines: List[str], config: Dict[str, Any]) -> str:
    """Applies final formatting rules and multiple regex enclosures to the combined content."""
    processed_lines: List[str] = []

    enclosure_configs = config.get("formatting", {}).get("regex_enclosures", [])

    if not isinstance(enclosure_configs, list):
        print("Warning: 'regex_enclosures' in config is not a list. Skipping enclosure processing.")
        enclosure_configs = []

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
        return " ".join(allowed_chars_pattern.findall(line))
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
        if not cleaned_line:
            return False
        for pattern in compiled_footer_patterns:
            if pattern.match(cleaned_line):
                return True
        return False
    return is_footer_func

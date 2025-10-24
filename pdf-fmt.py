#!/usr/bin/env python

# Copyright (c) 2025 bladeacer
# Licensed under the GPLv3 License. See LICENSE file for details.

import sys
import os
import re
import yaml
import argparse
import platform
import subprocess
from typing import List, Dict, Any, Tuple

CONFIG_FILENAME = "pdf-fmt.yaml"
SCRIPT_VERSION = "1.4.2"
DEFAULT_CHARS_REGEX = r"[a-zA-Z0-9\s!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~]+"
DEFAULT_CONVERT_FORMATS = ['pptx', 'ppt', 'doc', 'docx', 'odt']
NBSP = '\u00A0'
NON_ALPHA_PATTERN = re.compile(r'[^a-zA-Z]')
IS_CI_BUILD = os.environ.get('PDF_FMT_CI_BUILD', '0') == '1'
_CONVERSION_TOOL_CACHE: str | None = None

def check_venv():
    """Checks if the script is running inside a virtual environment (.venv).
    
    This check is skipped if the script is compiled (frozen) or running in a CI environment.
    """
    if getattr(sys, 'frozen', False) or IS_CI_BUILD:
        return
    
    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path or not venv_path.endswith('.venv'):
        print("Error: Script must be run from the '.venv' virtual environment.")
        print("Please activate it first (e.g., 'source .venv/bin/activate').")
        sys.exit(1)


def find_conversion_tool() -> str | None:
    """Checks for LibreOffice CLI (soffice) or Pandoc binary.
    
    The result is cached globally to avoid repeated subprocess calls.
    If IS_CI_BUILD is True, the expensive check is skipped.
    """
    global _CONVERSION_TOOL_CACHE
    
    if _CONVERSION_TOOL_CACHE is not None:
        return _CONVERSION_TOOL_CACHE

    if IS_CI_BUILD:
        print("INFO: Skipping conversion tool check due to CI environment flag.")
        _CONVERSION_TOOL_CACHE = None
        return None
    
    soffice_names = ['soffice', 'libreoffice', 'lowriter', 'swriter']
    for name in soffice_names:
        try:
            subprocess.run([name, '--version'], check=True, capture_output=True, timeout=5)
            _CONVERSION_TOOL_CACHE = name
            return name
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
            
    try:
        subprocess.run(['pandoc', '--version'], check=True, capture_output=True, timeout=5)
        _CONVERSION_TOOL_CACHE = 'pandoc'
        return 'pandoc'
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        _CONVERSION_TOOL_CACHE = None
        return None

check_venv()

try:
    import fitz
    import pyperclip
except ImportError as e:
    print(f"Error: A required library failed to import: {e}. Please ensure dependencies are installed.")
    sys.exit(1)

try:
    from breame.spelling import get_american_spelling, get_british_spelling
except ImportError:
    if not getattr(sys, 'frozen', False):
        print("Error: The 'breame' library is required for spelling enforcement.")
        print("Please run: pip install breame")
        sys.exit(1)
    def get_american_spelling(word: str) -> str: return word
    def get_british_spelling(word: str) -> str: return word


def find_config_file(filename: str) -> str | None:
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

def load_patterns_from_yaml(file_path: str | None) -> Dict[str, Any]:
    """Loads config data from a YAML file."""
    if not file_path:
        print(f"Warning: Configuration file '{CONFIG_FILENAME}' not found in any standard location. Using defaults.")
        return {}
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
            print(f"INFO: Loaded configuration from: {file_path}")
            return config if isinstance(config, dict) else {}
    except Exception as e:
        print(f"Error: Could not read or parse '{file_path}': {e}. Using defaults.")
        return {}

def convert_to_pdf(input_path: str, supported_formats: List[str]) -> Tuple[str | None, bool | None]:
    """Converts a non-PDF file to PDF using LibreOffice CLI or Pandoc."""
    file_ext = input_path.split('.')[-1].lower()
    if file_ext == 'pdf':
        return input_path, False 
        
    if file_ext not in supported_formats:
        print(f"Error: Input file format (.{file_ext}) is not supported for conversion to PDF.")
        print(f"Supported formats: {', '.join(supported_formats)}.")
        return None, None
    
    conversion_tool = find_conversion_tool()
    if not conversion_tool:
        print("Error: File conversion failed. Neither LibreOffice CLI ('soffice', 'lowriter') nor 'pandoc' was found.")
        print("Please ensure **LibreOffice** or **Pandoc** is installed and available in your system's PATH.")
        return None, None
    
    output_dir = os.path.dirname(input_path) or os.getcwd()
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    temp_pdf_path = os.path.join(output_dir, base_name + ".pdf")
    
    command: List[str] = []
    expected_output = ""
    
    if 'soffice' in conversion_tool or 'writer' in conversion_tool:
        print(f"INFO: Attempting to convert '{file_ext.upper()}' to PDF using LibreOffice CLI...")
        command = [
            conversion_tool, 
            '--headless', 
            '--convert-to', 
            'pdf', 
            input_path, 
            '--outdir', 
            output_dir
        ]
        expected_output = os.path.join(output_dir, base_name + ".pdf")
        
    elif conversion_tool == 'pandoc':
        print(f"INFO: Attempting to convert '{file_ext.upper()}' to PDF using Pandoc...")
        command = [
            'pandoc', 
            input_path, 
            '-o', 
            temp_pdf_path
        ]
        expected_output = temp_pdf_path

    try:
        process = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=120
        )
        
        if process.returncode != 0:
            print(f"Error: Conversion failed (Exit Code {process.returncode}).")
            print(f"Tool used: {conversion_tool}")
            print(f"STDOUT: {process.stdout.decode().strip()}")
            print(f"STDERR: {process.stderr.decode().strip()}")
            return None, None
            
        if os.path.exists(expected_output):
            print("INFO: Conversion successful.")
            return expected_output, True
        else:
            print(f"Error: Conversion succeeded, but output file was not found at {expected_output}.")
            return None, None
            
    except subprocess.TimeoutExpired:
        print("Error: File conversion timed out after 120 seconds.")
        return None, None
    except Exception as e:
        print(f"Conversion failed due to an unexpected error: {e}")
        return None, None

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

def enforce_spelling(text: str, locale: str) -> str:
    """Enforces US or UK spelling using the breame library, preserving case."""
    
    def process_word(word: str) -> str:
        clean_word = NON_ALPHA_PATTERN.sub('', word)
        
        if not clean_word:
            return word

        try:
            word_to_lookup = clean_word.lower()
            if locale == "EN-US":
                base_converted = get_american_spelling(word_to_lookup)
            elif locale == "EN-UK":
                base_converted = get_british_spelling(word_to_lookup)
            else:
                base_converted = clean_word.lower()
        except ValueError:
            base_converted = clean_word
            
        case_preserved_word = preserve_case(clean_word, base_converted)
        
        return word.replace(clean_word, case_preserved_word, 1)

    return " ".join(process_word(word) for word in text.split())

def clean_and_lint_text(text: str, locale: str) -> str:
    """Applies spelling linting and then cleans up spacing."""
    if locale in ["en-us", "en-uk"]:
        text = enforce_spelling(text, locale.upper())
    text = replace_successive_spaces(text)
    return text

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
        compiled_pattern = re.compile(pattern)
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

def extract_text_from_pdf(pdf_path: str, config: Dict[str, Any], compiled_filters: Dict[str, Any]) -> Tuple[str | None, str | None]:
    """Extracts text, applies line filters/linting, and handles line joining/splitting."""
    if not os.path.exists(pdf_path): 
        return None, f"Error: PDF file not found at '{pdf_path}'"

    linting_config = config.get("filters", {}).get("linting", {})
    formatting_config = config.get("formatting", {})
    
    spelling_locale = linting_config.get("spelling", {}).get("enforce_locale", "none").lower()
    min_chars = formatting_config.get("min_chars_per_line", 0)
    max_chars = formatting_config.get("max_chars_per_line", 80)
    
    enforce_cap = formatting_config.get("enforce_line_capitalization", False)
    page_sep_mode = formatting_config.get("page_separator", "--- PAGE SEPARATOR ---")
    
    extracted_lines: List[str] = []
    
    try:
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text") 
            
            if page_num > 0 and page_sep_mode != "none":
                if page_sep_mode == "___":
                    extracted_lines.append("___")
                elif page_sep_mode == "--- PAGE SEPARATOR ---":
                    extracted_lines.append("\n--- PAGE SEPARATOR ---")
                
            current_page_lines: List[str] = []
            
            for raw_line in page_text.split('\n'):
                filtered_line = compiled_filters['filter_line_content'](raw_line)
                
                if compiled_filters['is_footer'](filtered_line):
                    continue
                    
                cleaned_line = clean_and_lint_text(filtered_line, spelling_locale)
                
                formatted_line = compiled_filters['format_indented_line'](cleaned_line)
                
                if formatted_line.strip():
                     current_page_lines.append(formatted_line)
            
            line_buffer = ""
            for line in current_page_lines:
                stripped_line = line.strip()
                
                is_list_item = stripped_line.startswith(('-', '*'))
                is_sentence_end = re.search(r'[.?!]$', stripped_line)
                
                if is_list_item or is_sentence_end or len(stripped_line) >= min_chars:
                    if line_buffer:
                        split_lines = split_and_format_line(line_buffer, max_chars, enforce_cap)
                        extracted_lines.extend(split_lines)
                    line_buffer = line
                else:
                    if line_buffer:
                        separator = " " if not line_buffer.endswith('-') else ""
                        line_buffer += separator + stripped_line
                    else:
                        line_buffer += stripped_line
            
            if line_buffer:
                split_lines = split_and_format_line(line_buffer, max_chars, enforce_cap)
                extracted_lines.extend(split_lines)
            
        doc.close()
    except Exception as e:
        return None, f"An error occurred during PDF parsing: {e}"
    
    content = post_process_content(extracted_lines, config)
    return content, None

def write_content_to_file(content: str, file_path: str):
    """Writes content to a specified text file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"SUCCESS: Extracted content written to '{file_path}'.")
    except Exception as e:
        print(f"Error: Could not write content to file '{file_path}'. {e}")

def copy_content(content: str):
    """Copies content to clipboard."""
    try:
        pyperclip.copy(content)
        print("SUCCESS: Extracted content copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"Warning: Could not copy to clipboard. Error: {e}")

def perform_post_actions(content: str, config: Dict[str, Any]):
    """Executes post-extraction actions (copy, write file)."""
    actions = config.get("actions", {})
    if actions.get("copy", False):
        copy_content(content)
        
    file_path = actions.get("write_file")
    if file_path and isinstance(file_path, str):
        expanded_path = os.path.expanduser(file_path)
        resolved_path = os.path.abspath(expanded_path)
        write_content_to_file(content, resolved_path)

def setup_cli():
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

if __name__ == "__main__":
    config_path = find_config_file(CONFIG_FILENAME)
    CONFIG = load_patterns_from_yaml(config_path)

    conversion_config = CONFIG.get("conversion", {})
    filter_config = CONFIG.get("filters", {})
    
    supported_formats = conversion_config.get("supported_formats", DEFAULT_CONVERT_FORMATS)
    
    LINE_REGEX_PATTERNS = filter_config.get("footer_regexes", [])
    if not isinstance(LINE_REGEX_PATTERNS, list):
        LINE_REGEX_PATTERNS = []
    CHARS_REGEX_STRING = filter_config.get("allowed_chars_regex", DEFAULT_CHARS_REGEX)
    if not isinstance(CHARS_REGEX_STRING, str):
        CHARS_REGEX_STRING = DEFAULT_CHARS_REGEX
        
    COMPILED_FOOTER_PATTERNS = compile_footer_patterns(LINE_REGEX_PATTERNS)
    ALLOWED_CHARS_PATTERN = re.compile(CHARS_REGEX_STRING)

    def filter_line_content(line: str) -> str:
        """Filters line to keep only allowed characters."""
        return " ".join(ALLOWED_CHARS_PATTERN.findall(line))

    def format_indented_line(line: str) -> str:
        """Converts single-space indentation to Markdown list item if not already a list."""
        normalized_line = line.replace(NBSP, ' ') 
        
        if normalized_line.startswith(' '):
            if not normalized_line.startswith('  '):
                if not re.match(r'^\s*[-*]', normalized_line.lstrip()):
                    return "- " + normalized_line[1:]
        return normalized_line
    
    def is_footer(line: str) -> bool:
        """Checks if a line matches any compiled footer patterns."""
        cleaned_line = line.strip()
        if not cleaned_line:
            return False
        for pattern in COMPILED_FOOTER_PATTERNS:
            if pattern.match(cleaned_line):
                return True
        return False

    COMPILED_FILTERS = {
        'filter_line_content': filter_line_content,
        'format_indented_line': format_indented_line,
        'is_footer': is_footer
    }
    
    args = setup_cli()
    input_file_path = args.file_path
    temp_file_created = False
    
    pdf_file_path, temp_file_created = convert_to_pdf(input_file_path, supported_formats)

    if not pdf_file_path:
        print("Error: File preparation failed. Exiting.")
        sys.exit(1)
        
    extracted_content, error_message = extract_text_from_pdf(pdf_file_path, CONFIG, COMPILED_FILTERS)
    
    if temp_file_created and os.path.exists(pdf_file_path):
        try:
            os.remove(pdf_file_path)
            print(f"INFO: Cleaned up temporary PDF file: {pdf_file_path}")
        except Exception as e:
            print(f"Warning: Could not remove temporary file: {pdf_file_path}. Error: {e}")

    if error_message:
        print(f"Error: Extraction failed.")
        print(f"Details: {error_message}")
        sys.exit(1)
        
    if extracted_content:
        print(extracted_content)
        perform_post_actions(extracted_content, CONFIG)


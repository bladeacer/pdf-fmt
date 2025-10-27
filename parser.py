import sys
import os
import re
import subprocess
import io
from typing import List, Dict, Any, Tuple, Callable, Optional, TYPE_CHECKING
from core import NON_ALPHA_PATTERN, IS_CI_BUILD, write_content_to_file
from core import (
    setup_cli, find_config_file, load_patterns_from_yaml,
    compile_footer_patterns, filter_line_content_factory,
    format_indented_line, is_footer_factory, CONFIG_FILENAME,
    DEFAULT_CONVERT_FORMATS, DEFAULT_CHARS_REGEX, CompiledFilters
)

from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams

if TYPE_CHECKING:
    from core import CompiledFilters

pdfminer_deps = None
pyperclip = None
get_american_spelling: Callable[[str], str] = lambda w: w
get_british_spelling: Callable[[str], str] = lambda w: w
_CONVERSION_TOOL_CACHE: Optional[str] = None

def execute_main_pipeline() -> None:
    """
    Executes the main pipeline: CLI setup, dependency imports, config loading, 
    filter compilation, conversion, extraction, cleanup, and post-actions.
    
    NOTE: This assumes check_venv() is run by the caller (if needed).
    """
    args = setup_cli()
    input_file_path = args.file_path

    _import_dependencies()

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

    COMPILED_FILTERS: CompiledFilters = {
        'filter_line_content': filter_line_content_factory(ALLOWED_CHARS_PATTERN),
        'format_indented_line': format_indented_line,
        'is_footer': is_footer_factory(COMPILED_FOOTER_PATTERNS)
    }

    pdf_file_path, temp_file_created_flag = convert_to_pdf(input_file_path, supported_formats)

    if not pdf_file_path:
        sys.exit(1)

    extracted_content, error_message = extract_text_from_pdf(
        pdf_file_path, CONFIG, COMPILED_FILTERS
    )

    if temp_file_created_flag and os.path.exists(pdf_file_path):
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

def _import_dependencies():
    """Dynamically imports non-stdlib dependencies and sets module-level variables."""
    global pyperclip, pdfminer_deps
    global get_american_spelling, get_british_spelling

    try:
        import pyperclip as pc
        pyperclip = pc
    except ImportError as e:
        print(f"Error: A required library failed to import: {e}. Please ensure dependencies are installed.")
        sys.exit(1)

    try:
        from breame.spelling import get_american_spelling as g_a, get_british_spelling as g_b
        get_american_spelling = g_a
        get_british_spelling = g_b
    except ImportError:
        if not getattr(sys, 'frozen', False):
            print("Error: The 'breame' library is required for spelling enforcement.")
            print("Please run: pip install breame")
            sys.exit(1)
        def stub_american(word: str) -> str: return word
        def stub_british(word: str) -> str: return word
        get_american_spelling = stub_american
        get_british_spelling = stub_british

def enforce_spelling(text: str, locale: str, ignore_list: List[str]) -> str:
    """Enforces US or UK spelling using the breame library, preserving case,
    while ignoring words specified in the ignore_list.
    """
    global get_american_spelling, get_british_spelling
    from core import preserve_case

    ignore_set = {s.lower() for s in ignore_list}

    def process_word(word: str) -> str:
        clean_word = NON_ALPHA_PATTERN.sub('', word)
        if not clean_word: return word

        word_to_lookup = clean_word.lower()

        if word_to_lookup in ignore_set:
            return word

        try:
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

def clean_and_lint_text(text: str, locale: str, ignore_list: List[str]) -> str:
    """Applies spelling linting and then cleans up spacing."""
    from core import replace_successive_spaces

    if locale in ["en-us", "en-uk"]:
        text = enforce_spelling(text, locale.upper(), ignore_list)
    text = replace_successive_spaces(text)
    return text

def copy_content(content: str):
    """Copies content to clipboard."""
    global pyperclip
    try:
        pyperclip.copy(content)
        print("SUCCESS: Extracted content copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"Warning: Could not copy to clipboard. Error: {e}")

def perform_post_actions(content: str, config: Dict[str, Any]):
    """Executes post-extraction actions (copy, write file)."""
    actions = config.get("actions", {})
    if actions.get("copy", True):
        copy_content(content)

    file_path = actions.get("write_file")
    if file_path and isinstance(file_path, str):
        expanded_path = os.path.expanduser(file_path)
        resolved_path = os.path.abspath(expanded_path)
        write_content_to_file(content, resolved_path)

def find_conversion_tool() -> Optional[str]:
    """Checks for LibreOffice CLI (soffice) or Pandoc binary. The result is cached globally."""
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

def convert_to_pdf(input_path: str, supported_formats: List[str]) -> Tuple[Optional[str], Optional[bool]]:
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

    i = 0
    while os.path.exists(temp_pdf_path):
        i += 1
        temp_pdf_path = os.path.join(output_dir, f"{base_name}_{i}.pdf")

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
            if process.stdout: print(f"STDOUT: {process.stdout.decode().strip()}")
            if process.stderr: print(f"STDERR: {process.stderr.decode().strip()}")
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

def extract_text_from_pdf(pdf_path: str, config: Dict[str, Any], compiled_filters: 'CompiledFilters') -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts text from a PDF using pdfminer.six, applies line filters/linting, 
    and handles line joining/splitting.
    """
    if not os.path.exists(pdf_path):
        return None, f"Error: PDF file not found at '{pdf_path}'"

    from core import split_and_format_line, post_process_content

    filter_line_content_func: Callable[[str], str] = compiled_filters['filter_line_content']
    format_indented_line_func: Callable[[str], str] = compiled_filters['format_indented_line']
    is_footer_func: Callable[[str], bool] = compiled_filters['is_footer']

    linting_config = config.get("filters", {}).get("linting", {})
    formatting_config = config.get("formatting", {})

    spelling_locale = linting_config.get("spelling", {}).get("enforce_locale", "none").lower()
    
    ignore_list = linting_config.get("ignore_locale_strings", [])
    if not isinstance(ignore_list, list):
        ignore_list = []
    
    min_chars = formatting_config.get("min_chars_per_line", 0)
    max_chars = formatting_config.get("max_chars_per_line", 80)

    enforce_cap = formatting_config.get("enforce_line_capitalization", False)
    page_sep_mode = formatting_config.get("page_separator", "--- PAGE SEPARATOR ---")

    extracted_lines: List[str] = []
    
    try:
        rsrcmgr = PDFResourceManager()
        retstr = io.StringIO()
        laparams = LAParams()
        
        device = TextConverter(rsrcmgr, retstr, laparams=laparams)
        
        with open(pdf_path, 'rb') as fp:
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            
            for page_num, page in enumerate(PDFPage.get_pages(fp)):
                if page_num > 0 and page_sep_mode != "none":
                    if page_sep_mode == "___":
                        extracted_lines.append("___")
                    elif page_sep_mode == "--- PAGE SEPARATOR ---":
                        extracted_lines.append("\n--- PAGE SEPARATOR ---")

                interpreter.process_page(page)

        raw_text = retstr.getvalue()
        device.close()
        retstr.close()
    
    except Exception as e:
        return None, f"An error occurred during PDF parsing (pdfminer.six): {e}"

    for page_num, page_text_block in enumerate(raw_text.split('\x0c')):
        
        if page_num > 0 and page_sep_mode != "none":
            pass
        
        current_page_lines: List[str] = []

        for raw_line in page_text_block.split('\n'):
            filtered_line = filter_line_content_func(raw_line)

            if is_footer_func(filtered_line):
                continue

            cleaned_line = clean_and_lint_text(filtered_line, spelling_locale, ignore_list)

            formatted_line = format_indented_line_func(cleaned_line)

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
                separator = " " if not line_buffer.endswith('-') else ""
                line_buffer += (separator + stripped_line) if line_buffer else stripped_line

        if line_buffer:
            split_lines = split_and_format_line(line_buffer, max_chars, enforce_cap)
            extracted_lines.extend(split_lines)

    content = post_process_content(extracted_lines, config)
    return content, None

import sys
import os
import re
import subprocess
import io
import multiprocessing 
import glob
from typing import List, Dict, Any, Tuple, Callable, Optional, TYPE_CHECKING, Set

from core import NON_ALPHA_PATTERN, write_content_to_file, DEFAULT_CONVERT_FORMATS, DEFAULT_CHARS_REGEX
from core import (
    compile_footer_patterns, filter_line_content_factory,
    format_indented_line, is_footer_factory
)
from startup import setup_cli, IS_CI_BUILD

from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams

pyperclip = None
get_american_spelling: Callable[[str], str] = lambda w: w
get_british_spelling: Callable[[str], str] = lambda w: w
_CONVERSION_TOOL_CACHE: Optional[str] = None

def _discard_similar_images(output_dir: str, discard_threshold: int) -> None:
    """
    Discards images in output_dir that are highly similar to others using perceptual hashing.
    Similarity is based on the Hamming distance of the pHash.

    Map the percentage threshold (e.g., 90) to a pHash Hamming distance tolerance.
    An 8x8 pHash returns a max distance of 64. 
    A difference of 10% (90% similarity) is a distance of ~6.

    We will use a tolerance of 7 for 90% similarity, which is a common safe value for pHash.
    The actual tolerance is typically calculated as: MAX_DIFF = (100 - discard_threshold) / 10
    """
    try:
        from PIL import Image
        import imagehash
    except ImportError:
        print("Warning: Image similarity check requires 'Pillow' and 'imagehash'. Skipping filter.")
        return


    hash_tolerance = int((100 - discard_threshold) * 0.7)
    if hash_tolerance < 1: hash_tolerance = 1
    
    unique_hashes: Set[imagehash.ImageHash] = set()
    total_files = 0
    discarded_count = 0
    
    for ext in ('*.png', '*.jpg', '*.jpeg'):
        for filename in glob.glob(os.path.join(output_dir, ext)):
            total_files += 1
            try:
                with Image.open(filename) as img:
                    current_hash = imagehash.phash(img, hash_size=8)
                    
                    is_duplicate = False
                    for unique_hash in unique_hashes:
                        if current_hash - unique_hash <= hash_tolerance:
                            is_duplicate = True
                            break
                    
                    if is_duplicate:
                        os.remove(filename)
                        discarded_count += 1
                    else:
                        unique_hashes.add(current_hash)
                        
            except Exception:
                continue

    print(f"INFO: Image similarity check completed. Discarded {discarded_count} out of {total_files} extracted files (Tolerance: {hash_tolerance}).")


def _extract_images_subprocess(pdf_path: str, output_dir: str) -> None:
    """Runs pdf2txt.py in a subprocess to extract images."""
    print(f"INFO: Attempting to extract images to '{output_dir}'...")
    print(os.getcwd())
    
    command = [
        "pdf2txt.py", 
        pdf_path,
        "--output-dir", output_dir
    ]
    
    try:
        subprocess.run(
            command,
            check=False, 
            capture_output=True,
            timeout=120
        )
        print("INFO: Image extraction subprocess completed.")
        
    except FileNotFoundError:
        print("Warning: 'pdf2txt.py' command not found. Cannot extract images.")
        print("Ensure pdfminer.six is installed and its scripts are in your PATH.")
    except subprocess.TimeoutExpired:
        print("Warning: Image extraction timed out.")
    except Exception as e:
        print(f"Warning: Image extraction failed due to error: {e}")

def _process_page_text_block(
    args: Tuple[
        int, 
        str, 
        Dict[str, Any], 
        str,
        List[re.Pattern],
        str,
        List[str]
    ]
) -> List[str]:
    """
    Helper function to process a single page block's text.
    It re-creates the filter functions locally using the picklable patterns.
    """
    page_num, page_text_block, config, allowed_chars_regex_string, raw_footer_patterns, spelling_locale, ignore_list = args
    
    from core import split_and_format_line
    from core import filter_line_content_factory, is_footer_factory, format_indented_line
    from core import compile_footer_patterns

    allowed_chars_pattern = re.compile(allowed_chars_regex_string)
    compiled_footer_patterns = compile_footer_patterns(raw_footer_patterns)

    filters_config = config.get("filters", {})
    linting_config = filters_config.get("linting", {})

    formatting_config = config.get("formatting", {})

    filter_line_content_func: Callable[[str], str] = filter_line_content_factory(allowed_chars_pattern)
    is_footer_func: Callable[[str], bool] = is_footer_factory(compiled_footer_patterns)
    format_indented_line_func: Callable[[str], str] = format_indented_line

    min_chars = formatting_config.get("min_chars_per_line", 0)
    max_chars = formatting_config.get("max_chars_per_line", 80)
    enforce_cap = formatting_config.get("enforce_line_capitalization", False)
    page_sep_mode = formatting_config.get("page_separator", "--- PAGE SEPARATOR ---")
    
    current_page_lines: List[str] = []

    separator_lines: List[str] = []
    if page_num > 0 and page_sep_mode != "none":
        if page_sep_mode == "___":
            separator_lines.append("___")
        elif page_sep_mode == "--- PAGE SEPARATOR ---":
            separator_lines.append(f"\n--- Page {page_num + 1} ---")
            
    for raw_line in page_text_block.split('\n'):
        filtered_line = filter_line_content_func(raw_line)

        if is_footer_func(filtered_line):
            continue

        cleaned_line = clean_and_lint_text(filtered_line, spelling_locale, ignore_list)

        formatted_line = format_indented_line_func(cleaned_line)

        if formatted_line.strip():
            current_page_lines.append(formatted_line)

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

def execute_main_pipeline(CONFIG: Dict[str, Any]) -> None:
    """
    Executes the main pipeline: CLI setup, dependency imports, config loading, 
    filter compilation, conversion, extraction, cleanup, and post-actions.
    """
    args = setup_cli()
    input_file_path = args.file_path

    _import_dependencies()

    conversion_config = CONFIG.get("conversion", {})
    filters_config = CONFIG.get("filters", {})
    linting_config = filters_config.get("linting", {})
    spelling_config = linting_config.get("spelling", {})

    supported_formats = conversion_config.get("supported_formats", DEFAULT_CONVERT_FORMATS)

    LINE_REGEX_PATTERNS = filters_config.get("footer_regexes", [])
    if not isinstance(LINE_REGEX_PATTERNS, list):
        LINE_REGEX_PATTERNS = []
    CHARS_REGEX_STRING = filters_config.get("allowed_chars_regex", DEFAULT_CHARS_REGEX)
    if not isinstance(CHARS_REGEX_STRING, str):
        CHARS_REGEX_STRING = DEFAULT_CHARS_REGEX

    spelling_locale = spelling_config.get("enforce_locale", "en-US")
    if not isinstance(spelling_locale, str):
        print("Warning: 'enforce_locale' in config is not a string. Defaulting to 'en-US'.")
        spelling_locale = "en-US"
        
    ignore_list = spelling_config.get("ignore_locale_strings", [])
    if not isinstance(ignore_list, list):
        print("Warning: 'ignore_locale_strings' in config is not a list. Defaulting to empty.")
        ignore_list = []
    
    COMPILED_FOOTER_PATTERNS = compile_footer_patterns(LINE_REGEX_PATTERNS)
    ALLOWED_CHARS_PATTERN = re.compile(CHARS_REGEX_STRING)

    pdf_file_path, temp_file_created_flag = convert_to_pdf(input_file_path, supported_formats)

    if not pdf_file_path:
        sys.exit(1)

    extracted_content, error_message = extract_text_from_pdf(
        pdf_file_path, CONFIG, CHARS_REGEX_STRING, LINE_REGEX_PATTERNS, spelling_locale, ignore_list
    )

    actions = CONFIG.get("actions", {})
    image_dir = actions.get("image_dir", None)
    image_discard_threshold = actions.get("image_discard_threshold", 90)

    try:
        threshold_int = int(image_discard_threshold)
        if not (0 <= threshold_int <= 100):
            raise ValueError
        image_discard_threshold = threshold_int
    except (ValueError, TypeError):
        image_discard_threshold = 90
    
    if image_dir and isinstance(image_dir, str):
        resolved_image_dir = os.path.abspath(os.path.expanduser(image_dir))
        os.makedirs(resolved_image_dir, exist_ok=True) 
        _extract_images_subprocess(pdf_file_path, resolved_image_dir)
        _discard_similar_images(resolved_image_dir, image_discard_threshold)
    
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
    global pyperclip
    global get_american_spelling, get_british_spelling

    try:
        import pyperclip as pc
        pyperclip = pc
    except ImportError:
        print("Warning: 'pyperclip' library not found. Clipboard functionality will be disabled.")
        pyperclip = None

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

    def process_word(word: str) -> str:
        clean_word = NON_ALPHA_PATTERN.sub('', word)
        if not clean_word: return word

        word_to_lookup = clean_word

        for s in ignore_list:
            if word_to_lookup.lower() in s.lower():
                return word

        try:
            if locale.upper() == "EN-US":
                base_converted = get_american_spelling(word_to_lookup)
            elif locale.upper() == "EN-UK":
                base_converted = get_british_spelling(word_to_lookup)
            else:
                base_converted = clean_word
        except ValueError:
            base_converted = clean_word

        case_preserved_word = preserve_case(clean_word, base_converted)
        return word.replace(clean_word, case_preserved_word, 1)

    return " ".join(process_word(word) for word in text.split())

def clean_and_lint_text(text: str, locale: str, ignore_list: List[str]) -> str:
    """Applies spelling linting and then cleans up spacing."""
    from core import replace_successive_spaces

    if locale.lower() in ["en-us", "en-uk"]:
        text = enforce_spelling(text, locale, ignore_list)
    text = replace_successive_spaces(text)
    return text

def copy_content(content: str):
    """Copies content to clipboard."""
    global pyperclip
    if pyperclip is None:
        print("Warning: Clipboard copy skipped as 'pyperclip' is not available.")
        return
        
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
        
        expected_output = os.path.join(output_dir, os.path.basename(input_path).rsplit('.', 1)[0] + ".pdf")

        final_pdf_path = os.path.join(output_dir, base_name + ".pdf")
        
        expected_output = final_pdf_path
        temp_pdf_path = final_pdf_path
        
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

        if 'soffice' in conversion_tool or 'writer' in conversion_tool:
            potential_output = os.path.join(output_dir, os.path.basename(input_path).rsplit('.', 1)[0] + ".pdf")
            if os.path.exists(potential_output):
                temp_pdf_path = potential_output 

        if process.returncode != 0:
            print(f"Error: Conversion failed (Exit Code {process.returncode}).")
            print(f"Tool used: {conversion_tool}")
            if process.stdout: print(f"STDOUT: {process.stdout.decode().strip()}")
            if process.stderr: print(f"STDERR: {process.stderr.decode().strip()}")
            return None, None

        if os.path.exists(temp_pdf_path):
            print("INFO: Conversion successful.")
            return temp_pdf_path, True
        else:
            print(f"Error: Conversion succeeded, but output file was not found at {temp_pdf_path}.")
            return None, None

    except subprocess.TimeoutExpired:
        print("Error: File conversion timed out after 120 seconds.")
        return None, None
    except Exception as e:
        print(f"Conversion failed due to an unexpected error: {e}")
        return None, None

def extract_text_from_pdf(
    pdf_path: str,
    config: Dict[str, Any],
    allowed_chars_regex_string: str,
    footer_regex_patterns: List[str],
    spelling_locale: str,
    ignore_list: List[str]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts raw text from a PDF using pdfminer.six's TextConverter, 
    applies line filters/linting, and handles line joining/splitting 
    via a multiprocessing pool.
    """

    if not os.path.exists(pdf_path):
        return None, f"Error: PDF file not found at '{pdf_path}'"

    from core import post_process_content

    raw_text = ""
    processing_config = config.get("processing", {})
    max_cores = max(1, os.cpu_count() - 1)
    cores_used = processing_config.get("cores", max_cores)
    
    try:
        cores_int = int(cores_used)
        if not (0 < cores_int < os.cpu_count()):
            raise ValueError
        cores_used = cores_int
    except (ValueError, TypeError):
        cores_used = max_cores

    try:
        rsrcmgr = PDFResourceManager()
        retstr = io.StringIO()
        laparams = LAParams()
        device = TextConverter(rsrcmgr, retstr, laparams=laparams)
        
        with open(pdf_path, 'rb') as fp:
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            for page in PDFPage.get_pages(fp):
                interpreter.process_page(page)

        raw_text = retstr.getvalue()
        device.close()
        retstr.close()
    
    except Exception as e:
        if 'device' in locals() and hasattr(device, 'close'):
            device.close()
        return None, f"An error occurred during PDF parsing (pdfminer.six): {e}"

    page_text_blocks = raw_text.split('\x0c')
    
    pool_args = [
        (
            page_num, 
            page_text_block, 
            config, 
            allowed_chars_regex_string, 
            footer_regex_patterns,
            spelling_locale,
            ignore_list
        )
        for page_num, page_text_block in enumerate(page_text_blocks)
    ]

    extracted_lines: List[str] = []
    
    if len(page_text_blocks) > 1:
        try:
            with multiprocessing.Pool(processes=cores_used) as pool:
                results = pool.map(_process_page_text_block, pool_args)
            
            for page_lines in results:
                extracted_lines.extend(page_lines)
                
        except Exception as e:
            print(f"Warning: Multiprocessing failed ({e}). Falling back to sequential processing.")
            for args in pool_args:
                extracted_lines.extend(_process_page_text_block(args))
    else:
        for args in pool_args:
            extracted_lines.extend(_process_page_text_block(args))
            
    content = post_process_content(extracted_lines, config)
    return content, None

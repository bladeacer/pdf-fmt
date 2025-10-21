#!/usr/bin/env python

# Copyright (c) 2025 bladeacer
# Licensed under the GPLv3 License. See LICENSE file for details.

import sys
import os

def check_venv():
    if getattr(sys, 'frozen', False):
        return

    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path or not venv_path.endswith('.venv'):
        print("Error: Script must be run from the '.venv' virtual environment.")
        print("Please activate it first (e.g., 'source .venv/bin/activate').")
        sys.exit(1)

check_venv()

import fitz
import re
import yaml
import pyperclip
import argparse

PATTERNS_FILE = "patterns.yaml"
SCRIPT_VERSION = "1.0.0"
DEFAULT_CHARS_REGEX = r"[a-zA-Z0-9\s!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~]+"

def filter_line_content(line):
    """Filters line to keep only allowed characters."""
    return " ".join(ALLOWED_CHARS_PATTERN.findall(line))

def format_indented_line(line):
    """Applies indentation formatting."""
    NBSP = '\u00A0'
    normalized_line = line.replace(NBSP, ' ')
    
    if normalized_line.startswith(' '):
        if not normalized_line.startswith('  '):
            return "- " + normalized_line[1:]
            
    return normalized_line

def is_footer(line):
    """Checks if a filtered line matches any compiled footer patterns."""
    cleaned_line = line.strip()
    if not cleaned_line:
        return False
        
    for pattern in COMPILED_FOOTER_PATTERNS:
        if pattern.match(cleaned_line):
            return True
            
    return False

def load_patterns_from_yaml(file_path):
    """Loads all configuration data from a YAML file with graceful error handling."""
    if not os.path.exists(file_path):
        print(f"Warning: Configuration file '{file_path}' not found. Using defaults.")
        return {}
    
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
            return config if isinstance(config, dict) else {}
            
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML syntax in '{file_path}': {e}. Using defaults.")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred while reading '{file_path}': {e}. Using defaults.")
        return {}

def compile_footer_patterns(patterns):
    """Compiles list of regex strings into regex objects."""
    regex_list = []
    for pattern_string in patterns:
        regex_list.append(re.compile(pattern_string, re.IGNORECASE))
    return regex_list

def extract_text_from_pdf(pdf_path):
    """Extracts, filters, and formats text from PDF."""
    if not os.path.exists(pdf_path):
        return None, f"Error: File not found at '{pdf_path}'"
    
    if not pdf_path.lower().endswith('.pdf'):
        return None, f"Error: Input file must have a '.pdf' extension (received {os.path.basename(pdf_path)})."

    extracted_lines = []
    try:
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")
            
            extracted_lines.append(f"\n--- PAGE {page_num + 1} ---")
            
            for raw_line in page_text.split('\n'):
                filtered_line = filter_line_content(raw_line)
                
                if is_footer(filtered_line):
                    continue

                formatted_line = format_indented_line(filtered_line)
                
                if formatted_line.strip():
                     extracted_lines.append(formatted_line)
            
        doc.close()
        
    except Exception as e:
        return None, f"An error occurred during parsing: {e}"
        
    return "\n".join(extracted_lines), None

def write_content_to_file(content, file_path):
    """Writes content to a specified text file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"SUCCESS: Extracted content written to '{file_path}'.")
    except Exception as e:
        print(f"Error: Could not write content to file '{file_path}'. {e}")

def copy_content(content):
    """Copies content to clipboard."""
    try:
        pyperclip.copy(content)
        print("SUCCESS: Extracted content copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"Warning: Could not copy to clipboard. Error: {e}")
        print("Ensure necessary dependencies (e.g., 'xclip' or 'xsel' on Linux) are installed.")

def perform_post_actions(content, config):
    """Executes actions defined in the YAML config after successful extraction."""
    actions = config.get("actions", {})
    
    if actions.get("copy", False):
        copy_content(content)
        
    file_path = actions.get("write_file")
    if file_path and isinstance(file_path, str):
        write_content_to_file(content, file_path)

def setup_cli():
    """Sets up the argparse CLI and handles flags."""
    parser = argparse.ArgumentParser(
        description="pdf-fmt\n\nCleanly extracts and formats text from a PDF document.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        'pdf_path', 
        nargs='?',
        default=None,
        help="Path to the PDF file to process."
    )
    
    parser.add_argument(
        '-v', '--version', 
        action='version', 
        version=f'%(prog)s {SCRIPT_VERSION}',
        help="Show script's version and exit."
    )
    
    args = parser.parse_args()
    
    if args.pdf_path is None:
        parser.print_help()
        sys.exit(0)
        
    return args

if __name__ == "__main__":
    CONFIG = load_patterns_from_yaml(PATTERNS_FILE)
    
    LINE_REGEX_PATTERNS = CONFIG.get("footer_regexes", [])
    if not isinstance(LINE_REGEX_PATTERNS, list):
        print("Error: 'footer_regexes' in YAML is not a list. Disabling footer exclusion.")
        LINE_REGEX_PATTERNS = []

    CHARS_REGEX_STRING = CONFIG.get("allowed_chars_regex", DEFAULT_CHARS_REGEX)
    if not isinstance(CHARS_REGEX_STRING, str):
        print("Error: 'allowed_chars_regex' in YAML is not a string. Using default character set.")
        CHARS_REGEX_STRING = DEFAULT_CHARS_REGEX
        
    COMPILED_FOOTER_PATTERNS = compile_footer_patterns(LINE_REGEX_PATTERNS)
    ALLOWED_CHARS_PATTERN = re.compile(CHARS_REGEX_STRING)

    args = setup_cli()
    pdf_file_path = args.pdf_path
    
    extracted_content, error_message = extract_text_from_pdf(pdf_file_path)
    
    if error_message:
        print(f"Error: Extraction failed.")
        print(f"Details: {error_message}")
        sys.exit(1)
    
    print(extracted_content)
    perform_post_actions(extracted_content, CONFIG)

#!/usr/bin/env python

# Copyright (c) 2025 bladeacer
# Licensed under the GPLv3 License. See LICENSE file for details.

import fitz
import sys
import os
import re
import yaml
import pyperclip

PATTERNS_FILE = "patterns.yaml"

DEFAULT_CHARS_REGEX = r"[a-zA-Z0-9\s!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~]+"

def check_venv():
    if getattr(sys, 'frozen', False):
        return

    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path or not venv_path.endswith('.venv'):
        print("Error: Script must be run from the '.venv' virtual environment.")
        print("Please activate it first (e.g., 'source .venv/bin/activate').")
        sys.exit(1)

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

check_venv()
CONFIG = load_patterns_from_yaml(PATTERNS_FILE)

LINE_REGEX_PATTERNS = CONFIG.get("footer_regexes", [])
if not isinstance(LINE_REGEX_PATTERNS, list):
    print("Error: 'footer_regexes' in YAML is not a list. Disabling footer exclusion.")
    LINE_REGEX_PATTERNS = []

CHARS_REGEX_STRING = CONFIG.get("allowed_chars_regex", DEFAULT_CHARS_REGEX)
if not isinstance(CHARS_REGEX_STRING, str):
    print("Error: 'allowed_chars_regex' in YAML is not a string. Using default character set.")
    CHARS_REGEX_STRING = DEFAULT_CHARS_REGEX

def compile_footer_patterns(patterns):
    """Compiles list of regex strings into regex objects."""
    regex_list = []
    for pattern_string in patterns:
        regex_list.append(re.compile(pattern_string, re.IGNORECASE))
    return regex_list

COMPILED_FOOTER_PATTERNS = compile_footer_patterns(LINE_REGEX_PATTERNS)
ALLOWED_CHARS_PATTERN = re.compile(CHARS_REGEX_STRING)

def filter_line_content(line):
    """Filters line to keep only allowed characters."""
    return " ".join(ALLOWED_CHARS_PATTERN.findall(line))
    
def is_footer(line):
    """Checks if a filtered line matches any compiled footer patterns."""
    cleaned_line = line.strip()
    if not cleaned_line:
        return False
        
    for pattern in COMPILED_FOOTER_PATTERNS:
        if pattern.match(cleaned_line):
            return True
            
    return False

def extract_text_from_pdf(pdf_path):
    """Extracts, filters, and formats text from PDF."""
    if not os.path.exists(pdf_path):
        return f"Error: File not found at '{pdf_path}'"

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

                if filtered_line.strip():
                     extracted_lines.append(filtered_line)
            
        doc.close()
        
    except Exception as e:
        return f"An error occurred during parsing: {e}"
        
    return "\n".join(extracted_lines)

def copy_content(content):
    """Copies content to clipboard."""
    try:
        pyperclip.copy(content)
        print("\nSUCCESS: Extracted content copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"\nWarning: Could not copy to clipboard. Error: {e}")
        print("Please ensure you have necessary dependencies installed for your OS (e.g., 'xclip' or 'xsel' on Linux).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf-fmt.py <path_to_pdf_file>")
        sys.exit(1)
        
    pdf_file_path = sys.argv[1]
    
    extracted_content = extract_text_from_pdf(pdf_file_path)
    
    print(extracted_content)
    copy_content(extracted_content)

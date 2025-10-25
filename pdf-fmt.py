#!/usr/bin/env python

# Copyright (c) 2025 bladeacer
# Licensed under the GPLv3 License. See LICENSE file for details.

import sys
from core import check_venv
from parser import execute_main_pipeline

def main():
    """Main execution logic for the local script."""
    check_venv()
    
    execute_main_pipeline()

if __name__ == "__main__":
    main()

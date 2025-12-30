# Copyright (c) 2025 bladeacer
# Licensed under the GPLv3 License. See LICENSE file for details.

import sys
from typing import Dict, Any

from pdf_fmt.startup import check_venv, check_not_root, StartupCheckError 

def main():
    """Main execution logic for the local script."""
    
    try:
        check_not_root()
        check_venv()
        
    except StartupCheckError as e:
        print(e.message)
        sys.exit(e.exit_code)
    except Exception as e:
        print(f"Unknown error: {e}")
        sys.exit(1)

    try:
        from pdf_fmt import config
        from parser import execute_main_pipeline
        
        CONFIG: Dict[str, Any] = config.load_config()
        
        execute_main_pipeline(CONFIG)
    except StartupCheckError as e:
        print(e.message)
        sys.exit(e.exit_code)
    except Exception as e:
        print(f"Unknown error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

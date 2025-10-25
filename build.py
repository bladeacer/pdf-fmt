import sys
from parser import execute_main_pipeline

def main():
    """Main execution logic for the CI/compiled executable."""
    try:
        execute_main_pipeline()
    except Exception as e:
        print(f"A critical error occurred in the build execution: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

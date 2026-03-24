def write_content_to_file(content: str, file_path: str):
    """Writes content to a specified text file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"SUCCESS: Extracted content written to '{file_path}'.")
    except Exception as e:
        print(f"Error: Could not write content to file '{file_path}'. {e}")

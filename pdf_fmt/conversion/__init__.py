import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

_TOOL_CACHE: Optional[str] = None


def find_conversion_tool() -> Optional[str]:
    """
    Finds an available conversion tool (LibreOffice or Pandoc).
    Checks environment flags and caches the result.
    """
    global _TOOL_CACHE
    if _TOOL_CACHE is not None:
        return _TOOL_CACHE

    tools_to_check = ['soffice', 'libreoffice', 'lowriter',
                      'swriter', 'pandoc']

    for tool in tools_to_check:
        try:
            # We only need to check if the binary exists and is executable
            subprocess.run(
                [tool, '--version'],
                check=True,
                capture_output=True,
                timeout=5
            )
            _TOOL_CACHE = tool
            return tool
        except (
            subprocess.CalledProcessError,
            FileNotFoundError, subprocess.TimeoutExpired
        ):
            continue

    return None


def convert_to_pdf(input_path: str, supported_formats: List[str]) -> Tuple[Optional[str], bool]:
    """
    Converts a supported file to PDF.
    Returns (path_to_pdf, was_converted).
    """
    src = Path(input_path).resolve()

    if src.suffix.lower() == '.pdf':
        return str(src), False

    if src.suffix.lstrip('.').lower() not in supported_formats:
        print(f"Error: Format {src.suffix} not in supported list: {supported_formats}")
        return None, False

    tool = find_conversion_tool()
    if not tool:
        print("Error: No conversion tool found (LibreOffice or Pandoc).")
        return None, False

    # Prepare output path
    output_dir = src.parent
    target_pdf = output_dir / f"{src.stem}.pdf"

    # Avoid overwriting existing PDFs by incrementing filename
    counter = 0
    while target_pdf.exists():
        counter += 1
        target_pdf = output_dir / f"{src.stem}_{counter}.pdf"

    cmd: List[str] = []

    is_libreoffice = any(name in tool for name in
                         ['soffice', 'libreoffice', 'writer'])

    if is_libreoffice:
        cmd = [tool, '--headless', '--convert-to', 'pdf',
               str(src), '--outdir', str(output_dir)]
    elif tool == 'pandoc':
        cmd = [tool, str(src), '-o', str(target_pdf)]

    try:
        print(f"INFO: Converting {src.name} via {tool}...")
        result = subprocess.run(
            cmd, capture_output=True,
            timeout=120, check=False
        )

        if result.returncode != 0:
            print(f"Error: {tool} failed with code {result.returncode}")
            return None, False

        # Handle LibreOffice's lack of custom output filename support
        if is_libreoffice:
            default_output = output_dir / f"{src.stem}.pdf"
            if default_output.exists() and default_output != target_pdf:
                default_output.replace(target_pdf)

        if target_pdf.exists():
            return str(target_pdf), True

        print(f"Error: Conversion finished but {target_pdf.name} was not found.")
        return None, False

    except subprocess.TimeoutExpired:
        print("Error: Conversion timed out.")
    except Exception as e:
        print(f"Error: Unexpected conversion failure: {e}")

    return None, False

from typing import List

from .extract import extract_images_from_pdf
from .format import post_process_images


def _extract_and_format_images(
    pdf_path: str,
    output_dir: str,
    format_list: List[str],
    fallback_size: int,
    cores_used: int
) -> None:
    """Extracts page images and converts them to the configured formats."""
    print(f"INFO: Starting extraction to '{output_dir}'...")
    success = extract_images_from_pdf(
        pdf_path=pdf_path,
        output_dir=output_dir,
        fallback_kb=fallback_size
    )
    if not success:
        print("Warning: Extraction failed.")
        return

    post_process_images(
        pdf_path=pdf_path,
        output_dir=output_dir,
        format_list=format_list,
        fallback_size_kb=fallback_size,
        cores_used=cores_used
    )

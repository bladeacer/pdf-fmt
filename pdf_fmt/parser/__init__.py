import multiprocessing
import os
import sys
from typing import Any, Dict, List

from pdf_fmt.conversion import convert_to_pdf
from pdf_fmt.core import DEFAULT_CHARS_REGEX, DEFAULT_CONVERT_FORMATS
from pdf_fmt.image import _discard_similar_images, _extract_and_format_images
from pdf_fmt.processing import extract_text_from_pdf, perform_post_actions
from pdf_fmt.spell import locale_checks
from pdf_fmt.startup import setup_cli


def _get_validated_cores(config: Dict[str, Any]) -> int:
    """Calculates and validates the number of CPU cores to use."""
    available = os.cpu_count() or 1
    max_cores = max(1, available - 1)
    cores = config.get("processing", {}).get("cores", max_cores)
    try:
        cores_int = int(cores)
        if 0 < cores_int < available:
            return cores_int
    except (ValueError, TypeError):
        pass
    return max_cores


def _get_image_formats(actions: Dict[str, Any]) -> List[str]:
    """Normalizes image format settings to a list of strings."""
    setting = actions.get('image_format', ['png'])
    if isinstance(setting, str):
        return [setting]
    if isinstance(setting, list) and setting:
        return setting
    return ['png']


def _run_image_pipeline(
    pdf_path: str,
    actions: Dict[str, Any],
    cores: int
) -> None:
    """Handles the extraction using YAML config values."""
    image_dir = actions.get("image_dir")
    if not isinstance(image_dir, str):
        return

    res_dir = os.path.abspath(os.path.expanduser(image_dir))
    os.makedirs(res_dir, exist_ok=True)

    fallback_size = actions.get('fallback_image_kb', 2000)
    formats = _get_image_formats(actions)

    proc = multiprocessing.Process(
        target=_extract_and_format_images,
        args=(pdf_path, res_dir, formats, fallback_size, cores)
    )

    print(f"INFO: Starting extraction (Max {fallback_size}KB, Formats: {formats})")
    proc.start()
    proc.join(timeout=120)

    if proc.is_alive():
        print("Warning: Image extraction timed out. Terminating.")
        proc.terminate()
        proc.join(timeout=30)
        if proc.is_alive():
            print("Warning: Image extraction did not stop. Killing.")
            proc.kill()
            proc.join(timeout=30)

    threshold = actions.get("image_discard_threshold", 95)
    _discard_similar_images(res_dir, threshold)


def execute_main_pipeline(config: Dict[str, Any]) -> None:
    """Coordinates conversion, extraction, image handling and output actions."""
    args = setup_cli()

    locale, ignores = locale_checks(config)

    conv_cfg = config.get("conversion", {})
    formats = conv_cfg.get("supported_formats", DEFAULT_CONVERT_FORMATS)
    pdf_path, is_temp = convert_to_pdf(args.file_path, formats)

    if not pdf_path:
        sys.exit(1)

    filt_cfg = config.get("filters", {})
    footers = filt_cfg.get("footer_regexes", [])
    if not isinstance(footers, list):
        footers = []

    chars = filt_cfg.get("allowed_chars_regex", DEFAULT_CHARS_REGEX)
    if not isinstance(chars, str):
        chars = DEFAULT_CHARS_REGEX

    content, error = extract_text_from_pdf(
        pdf_path, config, chars, footers, locale, ignores
    )

    _run_image_pipeline(pdf_path, config.get("actions", {}), _get_validated_cores(config))

    if is_temp and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
            print(f"INFO: Cleaned up temporary PDF: {pdf_path}")
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")

    if error:
        print(f"Error: Extraction failed.\nDetails: {error}")
        sys.exit(1)

    if content:
        print(content)
        perform_post_actions(content, config)

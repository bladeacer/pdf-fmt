"""Image extraction subprocess."""

import multiprocessing
import os
from typing import Any, Dict, List

from pdf_fmt.image import _discard_similar_images, _extract_and_format_images


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

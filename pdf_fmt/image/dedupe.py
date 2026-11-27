import base64
import io
import os
import re
from typing import List

from PIL import Image

from .format import _get_format_details

_SVG_DATA = re.compile(r'data:image/png;base64,([A-Za-z0-9+/=]+)')


def _calculate_dhash(image: Image.Image, hash_size: int = 8) -> int:
    """Computes a difference hash for one image."""
    img = image.convert("L").resize(
        (hash_size + 1, hash_size), Image.Resampling.LANCZOS
    )
    pixels = list(img.getdata())

    diff_hash = 0
    for row in range(hash_size):
        for col in range(hash_size):
            idx = row * (hash_size + 1) + col
            if pixels[idx] > pixels[idx + 1]:
                diff_hash |= 1 << (row * hash_size + col)
    return diff_hash


def _hamming_distance(h1: int, h2: int) -> int:
    """Counts the differing bits between two hashes."""
    return (h1 ^ h2).bit_count()


def _discard_similar_images(output_dir: str, discard_threshold: int) -> None:
    """Removes images whose difference hashes fall inside the tolerance."""
    hash_tolerance = int((100 - discard_threshold) * 0.64)
    unique_hashes: List[int] = []
    total_files, discarded_count = 0, 0

    supported_exts = set(Image.registered_extensions().keys())
    supported_exts.add('.svg')
    files_to_check = []
    for name in os.listdir(output_dir):
        ext = os.path.splitext(name)[1].lower()
        if ext in supported_exts and _get_format_details(ext.lstrip('.')):
            files_to_check.append(os.path.join(output_dir, name))
    files_to_check.sort()

    for filename in files_to_check:
        total_files += 1
        try:
            current_hash = None
            if filename.lower().endswith('.svg'):
                with open(filename, 'r') as source:
                    match = _SVG_DATA.search(source.read())
                if match:
                    data = base64.b64decode(match.group(1))
                    with Image.open(io.BytesIO(data)) as img:
                        current_hash = _calculate_dhash(img)
            else:
                with Image.open(filename) as img:
                    current_hash = _calculate_dhash(img)

            if current_hash is None:
                continue

            is_duplicate = False
            for existing in unique_hashes:
                if _hamming_distance(current_hash, existing) <= hash_tolerance:
                    os.remove(filename)
                    discarded_count += 1
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_hashes.append(current_hash)
        except Exception as e:
            print(f"Warning: Image de-duplication failed: {e}")

    print(f"INFO: Similarity check (Tolerance: {hash_tolerance} bits):")
    print(f"      Discarded {discarded_count}/{total_files} images.")

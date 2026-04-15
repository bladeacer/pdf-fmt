import os
import re
import io
import glob
import time
import base64
import multiprocessing

from PIL import Image
from typing import Optional, List, Tuple

import pdfplumber

COMPLEX_PAGENUM_REGEX = re.compile(r'-\s*p(\d+)-\d+\.')
simple_page_str: str = r'(?:Image|Im|img_)(\d+)(?:\.\d+)?(?:\.\d+)?\.'
SIMPLE_PAGENUM_REGEX = re.compile(simple_page_str)

PDFPLUMBER_OUTPUT_REGEX = re.compile(r'^temp_raw_img_\d+\.')
_ImageProcessArgs = Tuple[str, str, List[str], int, str, int]


def _get_format_details(format_str: str) -> Optional[Tuple[str, str]]:
    normalized = format_str.upper()
    if normalized in ['JPG', 'JPEG']:
        return ('JPEG', '.jpg')
    if normalized == 'SVG':
        return ('SVG', '.svg')

    # Check Pillow registry
    for ext, fmt in Image.registered_extensions().items():
        if fmt == normalized:
            return (normalized, ext)
    return None


def extract_images_from_pdf(
    pdf_path: str,
    output_dir: str,
    password: str = "",
    fallback_kb: int = 2000
) -> bool:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            img_counter = 0
            for page in pdf.pages:
                page.extract_tables()
                for img_obj in page.images:
                    img_counter += 1
                    # Save initial high-res source as PNG
                    img_path = os.path.join(output_dir, f"temp_raw_img_{img_counter}.png")
                    bbox = (img_obj["x0"], img_obj["top"], img_obj["x1"], img_obj["bottom"])

                    for res in [400, 300, 200, 150, 72]:
                        try:
                            img_data = page.within_bbox(bbox).to_image(resolution=res)
                            img_data.save(img_path)
                            if os.path.getsize(img_path) / 1024 <= fallback_kb:
                                break
                        except Exception:
                            continue
        return True
    except Exception as e:
        print(f"Warning: Extraction failed: {e}")
        return False


def _process_single_image(args: _ImageProcessArgs) -> Optional[str]:
    (original_path, base_name, format_list, fallback_size_kb, timestamp, im_id) = args
    output_dir = os.path.dirname(original_path)

    try:
        with Image.open(original_path) as img:
            img_rgb = img.convert('RGB') if img.mode in ('RGBA', 'P') else img

            # Default fallback if all in list exceed size
            final_pillow_format, final_ext = ('PNG', '.png')

            for fmt_str in format_list:
                details = _get_format_details(fmt_str)
                if not details:
                    continue

                pillow_fmt, ext = details

                # Handle SVG output specifically
                if pillow_fmt == 'SVG':
                    new_filename = os.path.join(output_dir, f"{base_name}_{timestamp}_p{im_id}_{im_id}.svg")
                    img.save(original_path)
                    _save_as_svg_wrapper(original_path, new_filename)
                    os.remove(original_path)
                    return None

                # Standard Raster Formats
                img_to_save = img if pillow_fmt == 'PNG' else img_rgb
                buf = io.BytesIO()
                img_to_save.save(buf, pillow_fmt, quality=90)

                if (len(buf.getvalue()) / 1024) <= fallback_size_kb:
                    final_pillow_format, final_ext = pillow_fmt, ext
                    break

            # Final Save for non-SVG formats
            new_name = f"{base_name}_{timestamp}_p{im_id}_{im_id}{final_ext}"
            final_path = os.path.join(output_dir, new_name)
            img_to_save = img if final_pillow_format == 'PNG' else img_rgb
            img_to_save.save(final_path, final_pillow_format, quality=90)

        os.remove(original_path)
        return None
    except Exception as e:
        return f"Warning: Failed {os.path.basename(original_path)}: {e}"


def _save_as_svg_wrapper(source_png: str, output_svg: str):
    """Wraps a raster image in an SVG container to provide SVG support."""
    with Image.open(source_png) as img:
        w, h = img.size

    # Minimalistic SVG wrapper embedding the high-res data
    import base64
    with open(source_png, "rb") as f:
        encoded = base64.b64encode(f.read()).decode('ascii')

    svg_content = f' <svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
    svg_content += f'<image href="data:image/png;base64,{encoded}" width="{w}" height="{h}"/></svg>'

    with open(output_svg, "w") as f:
        f.write(svg_content)


def post_process_images(
    pdf_path: str,
    output_dir: str,
    format_list: List[str],
    fallback_size_kb: int,
    cores_used: int
):
    filename = os.path.basename(pdf_path)
    pdf_base_name = os.path.splitext(filename)[0].replace(' ', '_')
    timestamp = time.strftime("%m-%d_%H-%M-%S", time.localtime())

    files_to_process: List[_ImageProcessArgs] = []
    image_id_counter = 0

    # Search for the temporary files created by pdfplumber
    for original_path in glob.glob(os.path.join(output_dir, "temp_raw_img_*")):
        image_id_counter += 1
        files_to_process.append((
            original_path, pdf_base_name, format_list,
            fallback_size_kb, timestamp, image_id_counter
        ))

    if files_to_process:
        max_cores = max(1, (os.cpu_count() or 2) - 1)
        final_cores = min(cores_used or max_cores, max_cores,
                          len(files_to_process))

        try:
            print(f"""INFO: Processing {len(files_to_process)} images
on {final_cores} cores.""")
            with multiprocessing.Pool(processes=final_cores) as pool:
                results = pool.map(_process_single_image, files_to_process)
            for result in [r for r in results if r]:
                print(result)
        except Exception as e:
            print(f"FATAL: Multiprocessing failed: {e}")


def _calculate_dhash(image: Image.Image, hash_size: int = 8) -> int:
    """
    Computes a Difference Hash (dHash).
    """
    img = image.convert("L").resize(
        (hash_size + 1, hash_size),
        Image.Resampling.LANCZOS
    )
    pixels = list(img.getdata())

    diff_hash = 0
    for row in range(hash_size):
        for col in range(hash_size):
            idx = row * (hash_size + 1) + col
            left = pixels[idx]
            right = pixels[idx + 1]

            if left > right:
                diff_hash |= 1 << (row * hash_size + col)

    return diff_hash


def _hamming_distance(h1: int, h2: int) -> int:
    """Calculates the number of differing bits between two hashes."""
    return (h1 ^ h2).bit_count()


def _discard_similar_images(output_dir: str, discard_threshold: int) -> None:
    """
    Removes similar images using a custom dHash implementation.
    Dynamically scans all extensions supported by Pillow and validated by _get_format_details.
    """
    hash_tolerance = int((100 - discard_threshold) * 0.64)
    unique_hashes: List[int] = []
    total_files, discarded_count = 0, 0

    supported_exts = set(Image.registered_extensions().keys())
    supported_exts.add('.svg')

    all_files = os.listdir(output_dir)
    files_to_check = []

    for f in all_files:
        ext = os.path.splitext(f)[1].lower()
        if ext in supported_exts:
            format_name = ext.lstrip('.')
            if _get_format_details(format_name):
                files_to_check.append(os.path.join(output_dir, f))

    files_to_check.sort()

    for filename in files_to_check:
        total_files += 1
        try:
            current_hash = None
            ext = os.path.splitext(filename)[1].lower()

            # SVG Wrapper
            if ext == '.svg':
                with open(filename, 'r') as f:
                    content = f.read()
                    match = re.search(
                        r'data:image/png;base64,([A-Za-z0-9+/=]+)',
                        content
                    )
                    if match:
                        img_data = base64.b64decode(match.group(1))
                        with Image.open(io.BytesIO(img_data)) as img:
                            current_hash = _calculate_dhash(img)

            else:
                with Image.open(filename) as img:
                    current_hash = _calculate_dhash(img)

            if current_hash is None:
                continue

            is_duplicate = False
            for h in unique_hashes:
                if _hamming_distance(current_hash, h) <= hash_tolerance:
                    os.remove(filename)
                    discarded_count += 1
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_hashes.append(current_hash)

        except Exception as e:
            print(f"Warning: Image de-duplication failed: {e}")
            continue

    print(f"INFO: Similarity check (Tolerance: {hash_tolerance} bits):")
    print(f"      Discarded {discarded_count}/{total_files} images.")


def _extract_and_format_images(
    pdf_path: str,
    output_dir: str,
    format_list: List[str],
    fallback_size: int,
    cores_used: int
) -> None:
    print(f"INFO: Starting extraction to '{output_dir}'...")
    success = extract_images_from_pdf(
        pdf_path=pdf_path,
        output_dir=output_dir,
        fallback_kb=fallback_size
    )

    if success:
        post_process_images(
            pdf_path=pdf_path,
            output_dir=output_dir,
            format_list=format_list,
            fallback_size_kb=fallback_size,
            cores_used=cores_used
        )
    else:
        print("Warning: Extraction failed.")

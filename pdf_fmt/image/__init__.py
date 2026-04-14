import os
import glob
import re
import io
import multiprocessing
import time
from PIL import Image
import imagehash
from typing import Optional, List, Tuple, Set

import pdfplumber

COMPLEX_PAGENUM_REGEX = re.compile(r'-\s*p(\d+)-\d+\.')
simple_page_str: str = r'(?:Image|Im|img_)(\d+)(?:\.\d+)?(?:\.\d+)?\.'
SIMPLE_PAGENUM_REGEX = re.compile(simple_page_str)

# Updated regex to catch the new naming convention from pdfplumber extraction
PDFPLUMBER_OUTPUT_REGEX = re.compile(r'^temp_raw_img_\d+\.')
_ImageProcessArgs = Tuple[str, str, List[str], int, str, int]


def _get_format_details(format_str: str) -> Optional[Tuple[str, str]]:
    """
    Normalizes the user-provided format string to Pillow's internal name.
    """
    normalized = format_str.upper()
    if normalized in ['JPG', 'JPEG']:
        return ('JPEG', '.jpg')
    elif normalized == 'PNG':
        return ('PNG', '.png')

    if normalized in Image.registered_extensions():
        return (normalized, f'.{format_str.lower()}')
    return None


def extract_images_from_pdf(
    pdf_path: str,
    output_dir: str,
    password: str = "",
) -> bool:
    """
    Extracts images from a PDF using pdfplumber.
    Conforms to pycodestyle and pyflakes.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            img_counter = 0
            for page in pdf.pages:
                page.extract_tables()

                for img_obj in page.images:
                    img_counter += 1
                    try:
                        img_path = os.path.join(
                            output_dir,
                            f"temp_raw_img_{img_counter}.png"
                        )

                        bbox = (
                            img_obj["x0"],
                            img_obj["top"],
                            img_obj["x1"],
                            img_obj["bottom"]
                        )

                        page.within_bbox(bbox).to_image(
                            resolution=200
                        ).save(img_path)

                    except Exception as e:
                        print(f"Warning: Image {img_counter} failed: {e}")
                        continue
        return True

    except Exception as e:
        print(f"Warning: PDF image extraction failed for '{pdf_path}': {e}")
        return False


def _process_single_image(args: _ImageProcessArgs) -> Optional[str]:
    """
    Worker function to process a single image file.
    """
    (original_path, base_name, format_list,
     fallback_size_kb, timestamp, im_id) = args

    output_dir = os.path.dirname(original_path)
    filename = os.path.basename(original_path)

    # Default to index 1 if parsing fails
    index_num_str = '1'
    simple_match = SIMPLE_PAGENUM_REGEX.search(filename)

    if simple_match:
        index_num_str = simple_match.group(1)

    try:
        with Image.open(original_path) as img:
            is_alpha = img.mode in ('RGBA', 'P')
            img_rgb = img.convert('RGB') if is_alpha else img

            final_format_str = format_list[-1]
            final_details = _get_format_details(final_format_str) or ('JPEG',
                                                                      '.jpg')
            final_pillow_format, final_ext = final_details

            for current_format_str in format_list:
                details = _get_format_details(current_format_str)
                if not details:
                    continue

                pillow_format, new_ext = details
                img_to_save = img if (pillow_format == 'PNG') else img_rgb

                temp_buffer = io.BytesIO()
                img_to_save.save(temp_buffer, pillow_format, quality=90)
                temp_size_kb = len(temp_buffer.getvalue()) / 1024

                if temp_size_kb <= fallback_size_kb:
                    final_pillow_format, final_ext = pillow_format, new_ext
                    break

            new_filen_base = f"{base_name}_{timestamp}_{index_num_str}_{im_id}"
            new_filename = os.path.join(output_dir, new_filen_base + final_ext)

            img_to_save = img if (final_pillow_format == 'PNG') else img_rgb
            img_to_save.save(new_filename, final_pillow_format, quality=90)

        if os.path.exists(new_filename):
            os.remove(original_path)
            return None
        return f"Error: Final file {new_filename} was not created."

    except (FileNotFoundError, Exception) as e:
        return f"""Warning: Failed to process image {filename}. Skipping.
Error: {e}"""


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


def _discard_similar_images(output_dir: str, discard_threshold: int) -> None:
    hash_tolerance = max(1, int((100 - discard_threshold) * 0.7))
    unique_hashes: Set[imagehash.ImageHash] = set()
    total_files, discarded_count = 0, 0

    for ext in ('*.png', '*.jpg', '*.jpeg'):
        for filename in glob.glob(os.path.join(output_dir, ext)):
            total_files += 1
            try:
                with Image.open(filename) as img:
                    current_hash = imagehash.phash(img)
                    hash_cond = any(current_hash - h <= hash_tolerance
                                    for h in unique_hashes)
                    if hash_cond:
                        os.remove(filename)
                        discarded_count += 1
                    else:
                        unique_hashes.add(current_hash)
            except Exception:
                continue
    print(f"""INFO: Similarity check:
Discarded {discarded_count}/{total_files}.""")


def _extract_and_format_images(
    pdf_path: str,
    output_dir: str,
    format_list: List[str],
    fallback_size: int,
    cores_used: int
) -> None:
    print(f"INFO: Starting extraction to '{output_dir}'...")
    success = extract_images_from_pdf(pdf_path=pdf_path, output_dir=output_dir)

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

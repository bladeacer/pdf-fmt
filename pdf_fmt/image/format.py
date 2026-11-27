import base64
import glob
import io
import multiprocessing
import os
import time
from typing import List, Optional, Tuple

from PIL import Image

_ImageProcessArgs = Tuple[str, str, List[str], int, str, int]


def _get_format_details(format_str: str) -> Optional[Tuple[str, str]]:
    """Maps a configured format name to its Pillow format and extension."""
    normalized = format_str.upper()
    if normalized in ['JPG', 'JPEG']:
        return ('JPEG', '.jpg')
    if normalized == 'SVG':
        return ('SVG', '.svg')

    for ext, fmt in Image.registered_extensions().items():
        if fmt == normalized:
            return (normalized, ext)
    return None


def _save_as_svg_wrapper(source_png: str, output_svg: str) -> None:
    """Wraps a raster image in an SVG container."""
    with Image.open(source_png) as img:
        width, height = img.size
    with open(source_png, "rb") as source:
        encoded = base64.b64encode(source.read()).decode('ascii')

    svg = (
        f'<svg width="{width}" height="{height}" '
        'xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink">'
        f'<image href="data:image/png;base64,{encoded}" '
        f'width="{width}" height="{height}"/></svg>'
    )
    with open(output_svg, "w") as target:
        target.write(svg)


def _process_single_image(args: _ImageProcessArgs) -> Optional[str]:
    """Converts one temporary image and returns an error message on failure."""
    (original_path, base_name, format_list, fallback_size_kb, timestamp, im_id) = args
    output_dir = os.path.dirname(original_path)

    try:
        with Image.open(original_path) as img:
            img_rgb = img.convert('RGB') if img.mode in ('RGBA', 'P') else img
            final_pillow_format, final_ext = ('PNG', '.png')
            img_to_save = img

            for fmt_str in format_list:
                details = _get_format_details(fmt_str)
                if not details:
                    continue

                pillow_fmt, ext = details
                if pillow_fmt == 'SVG':
                    svg_name = f"{base_name}_{timestamp}_p{im_id}_{im_id}.svg"
                    img.save(original_path)
                    _save_as_svg_wrapper(
                        original_path, os.path.join(output_dir, svg_name)
                    )
                    os.remove(original_path)
                    return None

                img_to_save = img if pillow_fmt == 'PNG' else img_rgb
                buf = io.BytesIO()
                img_to_save.save(buf, pillow_fmt, quality=90)
                if (len(buf.getvalue()) / 1024) <= fallback_size_kb:
                    final_pillow_format, final_ext = pillow_fmt, ext
                    break

            new_name = f"{base_name}_{timestamp}_p{im_id}_{im_id}{final_ext}"
            final_path = os.path.join(output_dir, new_name)
            img_to_save = img if final_pillow_format == 'PNG' else img_rgb
            img_to_save.save(final_path, final_pillow_format, quality=90)

        os.remove(original_path)
        return None
    except Exception as e:
        return f"Warning: Failed {os.path.basename(original_path)}: {e}"


def post_process_images(
    pdf_path: str,
    output_dir: str,
    format_list: List[str],
    fallback_size_kb: int,
    cores_used: int
) -> None:
    """Converts all temporary images in parallel and prints any failures."""
    filename = os.path.basename(pdf_path)
    pdf_base_name = os.path.splitext(filename)[0].replace(' ', '_')
    timestamp = time.strftime("%m-%d_%H-%M-%S", time.localtime())

    files_to_process: List[_ImageProcessArgs] = []
    image_id_counter = 0
    for original_path in glob.glob(os.path.join(output_dir, "temp_raw_img_*")):
        image_id_counter += 1
        files_to_process.append((
            original_path, pdf_base_name, format_list,
            fallback_size_kb, timestamp, image_id_counter
        ))

    if not files_to_process:
        return

    max_cores = max(1, (os.cpu_count() or 2) - 1)
    final_cores = min(cores_used or max_cores, max_cores, len(files_to_process))
    print(f"INFO: Processing {len(files_to_process)} images on {final_cores} cores.")
    try:
        with multiprocessing.Pool(processes=final_cores) as pool:
            results = pool.map(_process_single_image, files_to_process)
        for result in [r for r in results if r]:
            print(result)
    except Exception as e:
        print(f"FATAL: Multiprocessing failed: {e}")

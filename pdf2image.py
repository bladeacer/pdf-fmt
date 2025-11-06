import os
import glob
import sys
import re
import io
import multiprocessing 
from typing import Any, Optional, Dict, List, Tuple
import time

try:
    import pdfminer.high_level
    from pdfminer.layout import LAParams
    from pdfminer.pdfexceptions import PDFValueError
except ImportError:
    print("FATAL: pdfminer.six not installed. Image extraction will fail.")
    pdfminer = None

try:
    from PIL import Image
    from PIL.Image import DecompressionBombError
except ImportError:
    print("Warning: Pillow not installed. Image post-processing is disabled.")
    Image = None
    DecompressionBombError = Exception


COMPLEX_PAGENUM_REGEX = re.compile(r'-\s*p(\d+)-\d+\.') 
SIMPLE_PAGENUM_REGEX = re.compile(r'(?:Image|Im)(\d+)(?:\.\d+)?(?:\.\d+)?\.')
PDFMINER_OUTPUT_REGEX = re.compile(r'^(?:Image|Im)\d+(?:\.\d+)*\.|^\w+-p\d+-\d+\.')
_ImageProcessArgs = Tuple[str, str, List[str], int, str, int]

def _get_format_details(format_str: str) -> Optional[Tuple[str, str]]:
    """
    Normalizes the user-provided format string (e.g., 'jpg', 'PNG') 
    to Pillow's internal name and the standard file extension.
    Returns (Pillow_Name, .ext) or None if invalid.
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
    laparams: Optional[LAParams] = None,
    password: str = "",
    disable_caching: bool = False,
    rotation: int = 0,
) -> bool:
    """
    Extracts images from a single PDF file using pdfminer.high_level.
    (Content remains unchanged from previous steps: handles the color error fix)
    """
    if pdfminer is None:
        return False
        
    try:
        with open(pdf_path, "rb") as fp:
            pdfminer.high_level.extract_text_to_fp(
                fp, 
                io.BytesIO(),
                output_type="text",
                codec="utf-8",
                laparams=laparams,
                maxpages=0,
                page_numbers=None,
                password=password,
                rotation=rotation,
                disable_caching=disable_caching,
                output_dir=output_dir, 
            )
        return True
    
    except PDFValueError as e:
        if "invalid float value" in str(e) or "Cannot set gray non-stroke color" in str(e):
             print(f"Warning: PDF color/pattern error encountered and ignored in '{pdf_path}'. Images may be missing. Error: {e}")
             return True
        raise 
    
    except Exception as e:
        print(f"Warning: PDF image extraction failed for '{pdf_path}'. Error: {e}")
        return False

def _process_single_image(args: _ImageProcessArgs) -> Optional[str]:
    """Worker function to process a single image file (compress, format, rename)."""
    
    original_path, pdf_base_name, format_list, fallback_size_kb, timestamp, image_id = args
    output_dir = os.path.dirname(original_path)
    filename = os.path.basename(original_path)
    index_num_str = '1'
    
    complex_match = COMPLEX_PAGENUM_REGEX.search(filename)
    
    if complex_match:
        index_num_str = complex_match.group(1).lstrip('0')
        if not index_num_str: index_num_str = '1'
    else:
        simple_match = SIMPLE_PAGENUM_REGEX.search(filename)
        if simple_match:
            index_num_str = simple_match.group(1).lstrip('0') 
            if not index_num_str: index_num_str = '1'
        else:
            return f"Warning: Could not parse page number from filename: {filename}. Defaulting to page 1."

    try:
        if not Image:
             return f"Error: Pillow not installed. Image processing skipped for {filename}"
             
        with Image.open(original_path) as img:
            is_alpha = img.mode in ('RGBA', 'P')
            img_rgb = img.convert('RGB') if is_alpha else img

            final_format_str = format_list[-1]
            final_details = _get_format_details(final_format_str)
            
            if not final_details:
                final_details = ('JPEG', '.jpg')
            
            final_pillow_format, final_ext = final_details
            
            for current_format_str in format_list:
                details = _get_format_details(current_format_str)
                if not details:
                    continue
                
                pillow_format, new_ext = details
                
                is_png_lossless = (pillow_format == 'PNG')
                img_to_save = img if is_png_lossless else img_rgb
                
                temp_buffer = io.BytesIO()
                
                # Use a standard quality of 90 for lossy formats
                img_to_save.save(temp_buffer, pillow_format, quality=90)
                temp_size_kb = len(temp_buffer.getvalue()) / 1024

                if temp_size_kb <= fallback_size_kb:
                    final_format_str = current_format_str
                    final_pillow_format = pillow_format
                    final_ext = new_ext
                    break
                
                print(f"INFO: Format {current_format_str.upper()} ({temp_size_kb:.0f}KB) exceeds {fallback_size_kb}KB. Trying next format...")

            new_filename_base = f"{pdf_base_name}_{timestamp}_{index_num_str}.{image_id}"
            new_filename = os.path.join(output_dir, new_filename_base + final_ext)
            
            is_png_lossless = (final_pillow_format == 'PNG')
            img_to_save = img if is_png_lossless else img_rgb
            img_to_save.save(new_filename, final_pillow_format, quality=90)

        if os.path.exists(new_filename):
            os.remove(original_path)
            return None
        
        return f"Error: Final file {new_filename} was not created."

    except (FileNotFoundError, DecompressionBombError, Exception) as e:
        return f"Warning: Failed to process image {filename}. Skipping. Error: {e}"


def post_process_images(
    pdf_path: str, 
    output_dir: str, 
    format_list: List[str],
    fallback_size_kb: int,
    cores_used: int
):
    """
    Collects image files and processes them concurrently using a multiprocessing Pool.
    """
    if not Image:
        print("Warning: Pillow not installed. Image post-processing is disabled.")
        return
        
    pdf_base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    pdf_base_name = pdf_base_name.replace(' ', '_')
    timestamp = time.strftime("%m-%d_%H-%M-%S", time.localtime())
    
    files_to_process: List[_ImageProcessArgs] = []
    image_id_counter = 0
    
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.bmp'): 
        for original_path in glob.glob(os.path.join(output_dir, ext)):
            filename = os.path.basename(original_path)
            
            if filename.lower().endswith('.bmp'):
                print(f"INFO: Discarding bitmap file: {filename} due to poor compression.")
                os.remove(original_path)
                continue 
            
            if not PDFMINER_OUTPUT_REGEX.search(filename):
                continue

            image_id_counter += 1
            
            files_to_process.append((
                original_path, 
                pdf_base_name, 
                format_list, 
                fallback_size_kb, 
                timestamp, 
                image_id_counter
            ))

    if files_to_process:
        max_available_cores = max(1, os.cpu_count() - 1)

        if cores_used is not None and cores_used > 0:
            final_cores_to_use = min(cores_used, max_available_cores)
        else:
            final_cores_to_use = max_available_cores
        
        final_cores_to_use = min(final_cores_to_use, len(files_to_process))
        
        try:
            print(f"INFO: Starting concurrent image processing using {len(files_to_process)} image files and {final_cores_to_use} cores.")
            with multiprocessing.Pool(processes=final_cores_to_use) as pool:
                results = pool.map(_process_single_image, files_to_process)
                
            for result in results:
                if result:
                    print(result)
                    
        except Exception as e:
            print(f"FATAL: Multiprocessing failed for image processing ({e}). Image files may be unprocessed or remain in their original formats.")

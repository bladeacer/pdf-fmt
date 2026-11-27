import os

import pdfplumber


def extract_images_from_pdf(
    pdf_path: str,
    output_dir: str,
    password: str = "",
    fallback_kb: int = 2000
) -> bool:
    """Renders page images to PNG at the highest resolution under the size cap."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            img_counter = 0
            for page in pdf.pages:
                page.extract_tables()
                for img_obj in page.images:
                    img_counter += 1
                    img_path = os.path.join(output_dir, f"temp_raw_img_{img_counter}.png")
                    bbox = (
                        img_obj["x0"], img_obj["top"],
                        img_obj["x1"], img_obj["bottom"],
                    )

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

from typing import Any, Dict, List, Optional, Tuple

from pdf_fmt.formatting import fix_spacing


def _get_page_elements(page, table_config: Dict[str, Any]) -> List[Tuple[float, str]]:
    """Returns tables and text blocks in page order."""
    tables = page.find_tables(table_settings=table_config)
    table_bboxes = [table.bbox for table in tables]

    def is_outside_tables(obj) -> bool:
        x0, top, x1, bottom = obj.get("x0"), obj.get("top"), obj.get("x1"), obj.get("bottom")
        if None in (x0, top, x1, bottom):
            return True
        for box in table_bboxes:
            if not (
                x1 < box[0] - 2 or x0 > box[2] + 2
                or bottom < box[1] - 2 or top > box[3] + 2
            ):
                return False
        return True

    elements: List[Tuple[float, str]] = []
    for table in tables:
        raw = table.extract()
        if raw:
            elements.append((table.bbox[1], _to_markdown_table(raw)))

    text = page.filter(is_outside_tables).extract_text(
        layout=True, use_text_flow=True, x_tolerance=2, y_tolerance=2
    )
    text = fix_spacing(text)
    if text:
        elements.append((0, text))

    elements.sort(key=lambda item: item[0])
    return elements


def _to_markdown_table(table: List[List[Optional[str]]]) -> str:
    """Converts an extracted table to Markdown, or to plain lines when broken."""
    if not table or len(table) < 1:
        return ""

    clean_table = [
        [" " if cell is None else cell.replace("\n", " ").strip() for cell in row]
        for row in table if any(cell is not None for cell in row)
    ]

    if len(clean_table) < 2 or not any(clean_table[0]):
        return "\n" + "\n".join(" ".join(row) for row in clean_table) + "\n"

    headers = clean_table[0]
    col_count = len(headers)
    lines = [
        f"| {' | '.join(headers)} |",
        f"| {' | '.join(['---'] * col_count)} |"
    ]
    for row in clean_table[1:]:
        row = row[:col_count] + [""] * (col_count - len(row))
        lines.append(f"| {' | '.join(row)} |")

    return "\n" + "\n".join(lines) + "\n"

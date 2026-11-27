"""Builds small real PDFs for end-to-end tests without extra dependencies."""


def _escape(text: str) -> bytes:
    """Escapes text for a PDF string literal."""
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)').encode('latin-1')


def _checkered(widget_width: int = 8) -> bytes:
    """Returns raw RGB bytes for a small checkerboard image."""
    size = widget_width
    return bytes(
        255 if (x + y) % 2 == 0 else 0
        for y in range(size) for x in range(size) for _ in range(3)
    )


def build_pdf(
    pages: list[list[str]],
    table: bool = False,
    image: bool = False,
) -> bytes:
    """Returns a PDF with text pages and, when asked, a table and an image."""
    cjk_lines = [
        line for page in pages for line in page
        if any(ord(char) > 127 for char in line)
    ]
    cjk_chars = sorted({char for line in cjk_lines for char in line})
    codes = {char: index + 1 for index, char in enumerate(cjk_chars)}

    def text_operator(line: str, y: int) -> bytes:
        prefix = f'BT /F1 12 Tf 60 {y} Td ('.encode()
        if all(ord(char) < 128 for char in line):
            return prefix + _escape(line) + b') Tj ET'
        encoded = bytes(codes[char] for char in line).hex().encode()
        return f'BT /F2 12 Tf 60 {y} Td <'.encode() + encoded + b'> Tj ET'

    first_page = [text_operator(line, 740 - 40 * index) for index, line in enumerate(pages[0])]
    if table:
        first_page.extend([
            b'q 0.5 w 60 600 m 300 600 l S 60 560 m 300 560 l S 60 520 m 300 520 l S',
            b'60 600 m 60 520 l S 180 600 m 180 520 l S 300 600 m 300 520 l S Q',
            b'BT /F1 11 Tf 70 580 Td (Name) Tj ET',
            b'BT /F1 11 Tf 190 580 Td (Value) Tj ET',
            b'BT /F1 11 Tf 70 540 Td (Alpha) Tj ET',
            b'BT /F1 11 Tf 190 540 Td (100) Tj ET',
        ])

    content_streams = [b'\n'.join(first_page)]
    for lines in pages[1:]:
        stream = [text_operator(line, 740 - 40 * index) for index, line in enumerate(lines)]
        if image and len(content_streams) == len(pages) - 1:
            stream.insert(0, b'q 100 0 0 100 60 600 cm /Im1 Do Q')
        content_streams.append(b'\n'.join(stream))

    font1_ref = 3 + len(pages) + len(content_streams)
    cursor = font1_ref + 1
    font2_ref = cursor if cjk_chars else None
    if font2_ref:
        cursor += 1
    cmap_ref = cursor if cjk_chars else None
    if cmap_ref:
        cursor += 1
    image_ref = cursor if image else None

    resources = b'<< /Font << /F1 ' + str(font1_ref).encode() + b' 0 R'
    if font2_ref:
        resources += b' /F2 ' + str(font2_ref).encode() + b' 0 R'
    resources += b' >>'
    if image_ref:
        resources += b' /XObject << /Im1 ' + str(image_ref).encode() + b' 0 R >>'
    resources += b' >>'

    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [' +
        b' '.join(f'{3 + index} 0 R'.encode() for index in range(len(pages))) +
        b'] /Count ' + str(len(pages)).encode() + b' >>',
    ]
    for index in range(len(pages)):
        objects.append(
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources '
            + resources + b' /Contents ' + str(3 + len(pages) + index).encode() + b' 0 R >>'
        )
    for stream in content_streams:
        objects.append(
            b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n'
            + stream + b'\nendstream'
        )
    objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    if font2_ref:
        objects.append(
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /ToUnicode '
            + str(cmap_ref).encode() + b' 0 R >>'
        )
        mapping = '\n'.join(
            f'<{code:02X}> <{ord(char):04X}>' for char, code in codes.items()
        )
        cmap = (
            '/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n'
            '/CMapName /Test def\n/CMapType 2 def\n1 begincodespacerange\n'
            '<00> <FF>\nendcodespacerange\n'
            f'{len(codes)} beginbfchar\n{mapping}\nendbfchar\nendcmap\n'
            'CMapName currentdict /CMap defineresource pop\nend\nend'
        ).encode()
        objects.append(
            b'<< /Length ' + str(len(cmap)).encode() + b' >>\nstream\n'
            + cmap + b'\nendstream'
        )
    if image_ref:
        pixels = _checkered(8)
        objects.append(
            b'<< /Type /XObject /Subtype /Image /Width 8 /Height 8'
            b' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length '
            + str(len(pixels)).encode() + b' >>\nstream\n' + pixels + b'\nendstream'
        )

    output = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(output)
    output += f'xref\n0 {len(objects) + 1}\n'.encode()
    output += b'0000000000 65535 f \n'
    for offset in offsets[1:]:
        output += f'{offset:010d} 00000 n \n'.encode()
    output += (
        f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
        f'startxref\n{xref}\n%%EOF\n'
    ).encode()
    return bytes(output)

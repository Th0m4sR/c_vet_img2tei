from pytesseract import pytesseract
from xml.sax.saxutils import escape
from lxml import etree
from typing import List
from pipeline.hocr_tools.hocr_helpers import get_element_bbox


def re_ocr_carea(page_bbox, page_image, carea, bbox_margins, remove_empty_lines: bool = True, psm: int = 6):
    x1, y1, x2, y2 = get_element_bbox(carea)
    # Re-OCR the carea with the page segmentation mode that detects a uniform block of text
    page_x1, page_y1, page_x2, page_y2 = page_bbox
    # Die bbox leicht zu erweitern verbessert die Ergebnisse deutlich;
    # Von x1 kann man ca. den x-merge-threshold abziehen
    # Es muss aber alles nach wie vor innerhalb des Bildes der Seite liegen
    x1_modifier = min(bbox_margins[0], x1 - page_x1)
    y1_modifier = min(bbox_margins[1], y1 - page_y1)
    x2_modifier = min(bbox_margins[2], page_x2 - x2)
    y2_modifier = min(bbox_margins[3], page_y2 - y2)
    bounding_box = (x1 - x1_modifier, y1 - y1_modifier, x2 + x2_modifier, y2 + y2_modifier)
    # Get all lines in the current carea
    text = escape(pytesseract.image_to_string(page_image.crop(bounding_box), lang='deu', config=f'--psm {psm}'))
    if remove_empty_lines:
        carea_lines = [line for line in text.split("\n") if len(line) > 0]
    else:
        carea_lines = text.split("\n")
    return carea_lines


def encode_carea_lines_as_p(carea_lines: List[str]) -> str:
    xml_lines = '<lb />'.join([escape(line) for line in carea_lines])
    new_text_element = etree.fromstring(f'<p>{xml_lines.strip()}</p>')
    return new_text_element

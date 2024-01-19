from lxml import etree
from pytesseract import pytesseract
from pipeline.hocr_tools.hocr_helpers import build_ocr_carea_text
from xml.sax.saxutils import escape
from pipeline.constants import NAMESPACES, EMPTY_HOCR_TREE

# from table_extraction import extract_page_table_boxes

"""
This module utilizes table_extraction to set up a table structure that is then encoded to TEI XML
"""


from pipeline.tei_encoding.table_processing import table_extraction
from PIL import Image
import re


FIRST_LEVEL_ENUMERATION_PATTERN = re.compile(r"^[a-z][\]\)\}]*\s")  # a)
SECOND_LEVEL_ENUMERATION_PATTERN = re.compile(r"^[a-z][a-z][\]\)\}]*\s")  # a)


def encode_table(ocr_page_element, ocr_page_image):
    # Initialize an empty table
    table = etree.Element("table")
    # Get the table_data_boxes
    td_boxes = table_extraction.extract_page_table_boxes(ocr_page_element=ocr_page_element, ocr_page_image=ocr_page_image)
    # Encode line_wise
    for td_box_line in td_boxes:
        tr_element = encode_table_row(ocr_page_image, td_box_line)
        table.append(tr_element)
    table_area = table_extraction.get_table_area_from_td_boxes(td_boxes)
    # Return the encoded table and the area that contains the table
    return table, table_area


def encode_table_row(ocr_page_image, table_row_areas):
    # Create the table row element
    tr_element = etree.Element("row")
    # Encode and append the table cells one by one and append them to the table row
    for table_cell_area in table_row_areas:
        td = encode_table_cell(ocr_page_image, table_cell_area)
        tr_element.append(td)
    return tr_element


def sanitize_line(line: str):
    """
    Takes a line and removes all special characters that are not * or . up to the first character
    :param line:
    :return:
    """
    pattern = re.compile(r'^[^a-zA-Z0-9*(.,$&§]*')
    modified_string = re.sub(pattern, '', line)
    return modified_string.strip()


def encode_table_cell(ocr_page_image: Image, table_cell_area):
    x1, y1, x2, y2 = table_cell_area
    td_element = etree.Element("cell")
    # print(table_cell_area)
    text_area_image = ocr_page_image.crop((x1, y1, x2, y2))
    new_ocr_string = pytesseract.run_and_get_output(text_area_image, 'hocr', 'deu', '--dpi 300', '--psm 6') if (y2-y1) * (x2-x1) > 0 else EMPTY_HOCR_TREE
    td_hocr_tree = etree.fromstring(bytes(new_ocr_string, 'utf-8'))

    enumeration_list = None
    current_element_lines = []

    first_level_enumeration_number = 1
    for ocr_carea in td_hocr_tree.xpath("//x:div[@class='ocr_carea']", namespaces=NAMESPACES):
        carea_lines = [sanitize_line(line) for line in build_ocr_carea_text(ocr_carea)]
        if len(carea_lines) == 0:
            td_text = etree.fromstring("<p/>")
            td_element.append(td_text)
            continue
        for line in carea_lines:
            # Detect new enumeration element
            if FIRST_LEVEL_ENUMERATION_PATTERN.match(line):
                # Check if a list exist
                if enumeration_list is None:
                    enumeration_list = etree.Element("list")
                # If an enumeration element was currently encoded, add it to the td_element's list
                if len(current_element_lines) > 0:
                    p_text = "<lb />\n".join([escape(line) for line in current_element_lines])
                    td_text = etree.fromstring(f'<item n="{first_level_enumeration_number}"><p>{p_text}</p></item>')
                    first_level_enumeration_number += 1
                    enumeration_list.append(td_text)
                current_element_lines = [line]
            else:
                # If there is no listing, just append the lines
                current_element_lines.append(escape(line))
    # --> From here, it is after the loop
    # After everything is done, append the list, if it exists
    if enumeration_list is not None:
        # If there are still lines to append, do it now
        if len(current_element_lines) > 0:
            p_text = "<lb />\n".join([escape(line) for line in current_element_lines])
            td_text = etree.fromstring(f'<item><p n="{first_level_enumeration_number}">{p_text}</p></item>')
            enumeration_list.append(td_text)
        # Append the list to the cell
        td_element.append(enumeration_list)
    else:
        # Else, set the td-element's text
        p_text = "<lb />\n".join([escape(line) for line in current_element_lines])
        td_text = etree.fromstring(f'<p>{p_text}</p>')
        td_element.append(td_text)
    return td_element

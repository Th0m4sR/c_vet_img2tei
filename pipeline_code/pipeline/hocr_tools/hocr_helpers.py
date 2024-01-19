from lxml import etree
from typing import List, Tuple
from copy import deepcopy
from ..constants import NAMESPACES


"""
Working on hOCR trees
"""


def combine_hocr_pages(hocr_trees: List[etree.ElementTree]) -> etree:
    """
    Takes a list of etrees that contain the parsed hOCR vet_files and combines all div tags with class='ocr_page' into one
    single tree. This results in a single etree that contains all pages
    :param hocr_trees: list of hOCR etrees
    :return: hOCR etree with all pages of the document
    """
    # Kann auch über cli mit hocr-tools (i.e., hocr-combine) gemacht werden
    doc_tree = deepcopy(hocr_trees[0])
    target_body = doc_tree.xpath("///x:body", namespaces=NAMESPACES)[0]
    for i in range(1, len(hocr_trees)):
        source_tree = deepcopy(hocr_trees[i])
        source_element = source_tree.xpath("///x:div[@class='ocr_page']", namespaces=NAMESPACES)[0]
        target_body.append(source_element)
        # Ensure the XML will be well-formed
        etree_string = etree.tostring(hocr_trees[i], pretty_print=True, encoding="unicode")
        try:
            doc = etree.fromstring(etree_string)
        except Exception:
            raise ValueError(f"Resulting XML was not well formed")
    return doc_tree


def remove_element_from_hocr_tree(hocr_element: etree.ElementTree):
    parent = hocr_element.getparent()
    if parent is not None:
        parent.remove(hocr_element)


"""
Accessing element attributes faster
"""


def get_element_bbox(hocr_element: etree.ElementTree):
    """
    Returns the element bbox x1, y1, x2, y2 of the input element
    :param hocr_element: element to get the bbox from
    :return: x1, y1, x2, y2 of the input element bbox
    """
    return list(map(int, hocr_element.attrib.get("title").split(";")[0].split(" ")[1:]))


def get_surrounding_bbox(hocr_element_list: List[etree.ElementTree]) -> Tuple[int, int, int, int]:
    """
    Takes a list of hOCR elements and returns x1, y1, x2, y2 that span a bbox around these elements
    :param hocr_element_list: list of parsed hOCR elements
    :return: x1, y1, x2, y2 that span a bbox around the elements in the hocr_element_list
    """
    bbox_coordinates = [list(get_element_bbox(elem)) for elem in hocr_element_list]
    x1 = min([b[0] for b in bbox_coordinates])
    y1 = min([b[1] for b in bbox_coordinates])
    x2 = max([b[2] for b in bbox_coordinates])
    y2 = max([b[3] for b in bbox_coordinates])
    return x1, y1, x2, y2


"""
Checking if elements overlap in any direction
"""


def ocr_elements_overlap_horizontally(hocr_elem_1, hocr_elem_2):
    _, e1_y1, _, e1_y2 = get_element_bbox(hocr_elem_1)
    _, e2_y1, _, e2_y2 = get_element_bbox(hocr_elem_2)
    if e1_y1 <= e2_y1 <= e1_y2 or e1_y1 <= e2_y2 <= e1_y2 or e2_y1 <= e1_y1 <= e2_y2 or e2_y1 <= e1_y2 <= e2_y2:  # e1_y2 < e2_y1 or e2_y2 < e1_y1:
        return True
    return False


def ocr_elements_overlap_vertically(hocr_elem_1, hocr_elem_2):
    e1_x1, _, e1_x2, _ = get_element_bbox(hocr_elem_1)
    e2_x1, _, e2_x2, _ = get_element_bbox(hocr_elem_2)
    if e1_x2 < e2_x1 or e2_x2 < e1_x1:
        return False
    return True


def ocr_elements_overlap(hocr_elem_1, hocr_elem_2):
    return ocr_elements_overlap_horizontally(hocr_elem_1, hocr_elem_2) and ocr_elements_overlap_horizontally(
        hocr_elem_1, hocr_elem_2)


"""
Getting text from hOCR trees and elements
"""


def print_hocr_tree(hocr_tree: etree.ElementTree):
    """
    Print the text in the order of the input hocr_tree
    :param hocr_tree: tree of which the text is printed
    :return:
    """
    text_pages = hocr_tree.xpath("///x:body/x:div[@class='ocr_page']", namespaces=NAMESPACES)
    for text_page in text_pages:
        text_careas = text_page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
        for text_carea in text_careas:
            text_pars = text_carea.xpath(".//x:p[@class='ocr_par']", namespaces=NAMESPACES)
            for text_par in text_pars:
                text_lines_or_floats = text_par.xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat']",
                                                      namespaces=NAMESPACES)
                for text_line_or_float in text_lines_or_floats:
                    text_ocr_words = text_line_or_float.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)
                    text_ocr_line = " ".join([w.text for w in text_ocr_words])
                    print(text_ocr_line)


def build_ocr_carea_texts(page_elem_tree: etree.ElementTree) -> List[List[str]]:
    """
    Finds all class='ocr_carea' div tags in the element tree and structures the text in lists:
    ocr_carea
    |-> ocr_line / ocr_textfloat
    |--> Words joined by ' '
    :param page_elem_tree: The element tree which will be splitted into its text
    :return: A list of lists (ocr_careas) that contain lists (ocr_line / ocr_textfloat) with lines
    """
    page_ocr_careas = page_elem_tree.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    parsed_ocr_careas = []  # This stores the corresponding area
    for area in page_ocr_careas:
        parsed_ocr_careas.append(build_ocr_carea_text(area))
    return parsed_ocr_careas


def build_ocr_carea_text(ocr_carea_elem: etree.Element) -> List[str]:
    """
    Takes a class='ocr_carea' element as input and formats its lines as text
    :param ocr_carea_elem: Element from which the text will be formatted
    :return: List of lines in the ocr_carea
    """
    text_elements = ocr_carea_elem.xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat' or @class='ocr_header']",
                                         namespaces=NAMESPACES)
    ocr_carea_lines = []
    for text_element in text_elements:
        x_word_spans = text_element.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)
        line = " ".join([w.text for w in x_word_spans if w.text is not None])
        ocr_carea_lines.append(line)
    return ocr_carea_lines

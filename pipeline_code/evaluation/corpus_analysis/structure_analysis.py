from lxml import etree
from pipeline.constants import TEI_NAMESPACE
from tei_tools import build_element_lines
import word_analysis


NAMESPACES = {'x': TEI_NAMESPACE}

TOC_LABEL = "contents"
TEIL_LABEL = "teil"
ABSCHNITT_LABEL = "abschnitt"
PARAGRAPH_LABEL = "paragraph"


def detect_text_structure(regulation_tree: etree.ElementTree):
    """
    Gets the text structure in a JSON string:
    {
        'headline': elem_headline,
        'lines': line_count,
        'words': word_count,
    }
    :param regulation_tree:
    :return:
    """
    # Get all section types
    divs = regulation_tree.xpath(".//x:div", namespaces=NAMESPACES)
    div_types = [div.attrib.get("type") for div in divs if "type" in div.attrib]
    all_text_elements = [TOC_LABEL, TEIL_LABEL, ABSCHNITT_LABEL, PARAGRAPH_LABEL]
    # Get all types of all possible types
    text_elements = [text_elem for text_elem in all_text_elements if text_elem in div_types]

    text_structure = {}
    for text_elem_idx in range(len(text_elements)):
        text_elem = text_elements[text_elem_idx]
        # Iterate over all possible child elements
        elem_divs = regulation_tree.xpath(f".//x:div[@type='{text_elem}']", namespaces=NAMESPACES)
        text_elem_info = []
        for elem_div in elem_divs:
            elem_headline = get_text_element_headline(elem_div)
            line_count = word_analysis.count_p_lines(elem_div)
            word_count = word_analysis.count_p_total_words(elem_div)
            text_elem_info.append(
                {
                    'headline': elem_headline,
                    'lines': line_count,
                    'words': word_count,
                }
            )
            # Hier könnte man sogar einfach nach Sub-Elementen zählen
        text_structure[text_elem] = text_elem_info
    return text_structure


def get_text_element_headline(text_element: etree.ElementTree) -> str:
    """
    Finds the first <head> element and returns its text
    :param text_element:
    :return:
    """
    elem_head = text_element.find('x:head', namespaces=NAMESPACES)
    combined_head_lines = "\n".join(build_element_lines(elem_head))
    return combined_head_lines


def count_pages(regulation_tree: etree.ElementTree) -> int:
    """
    Count the document pages
    :param regulation_tree:
    :return:
    """
    return len(regulation_tree.xpath(".//x:pb", namespaces=NAMESPACES))


def get_deepest_nesting(regulation_tree: etree.ElementTree) -> int:
    """
    Finds the deepest nested element in the document
    :param regulation_tree:
    :return:
    """
    text_segments = regulation_tree.findall(".//*[@text_level]")
    text_levels = list(map(int, [text_segment.get('text_level') for text_segment in text_segments]))
    max_nesting = max(text_levels) if len(text_levels) > 0 else -1
    return max_nesting

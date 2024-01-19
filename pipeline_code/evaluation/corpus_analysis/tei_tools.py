from lxml import etree
from pipeline.constants import TEI_NAMESPACE


NAMESPACES = {'x': TEI_NAMESPACE}


def build_element_lines(tei_element: etree.ElementTree):
    """
    Creates a list of all lines that are separated by <lb/>-tags in the input element
    :param tei_element:
    :return:
    """
    lines = [tei_element.text] if tei_element.text is not None else []
    for next_line in tei_element.findall('x:lb', namespaces=NAMESPACES):
        lines.append(next_line.tail.strip() if next_line.tail else '')
    return lines


def get_document_year(regulation_tree: etree.ElementTree) -> int:
    """
    Gets the release year of the document
    :param regulation_tree:
    :return:
    """
    date = regulation_tree.find('.//x:date', namespaces=NAMESPACES)
    try:
        result = int(date.text.split(" ")[-1])
    except Exception as e:
        result = 0
    return result


def get_document_title(regulation_tree: etree.ElementTree) -> str:
    """
    Gets the title of the document
    :param regulation_tree:
    :return:
    """
    title = regulation_tree.find('.//x:title', namespaces=NAMESPACES)
    if title is None:
        return 'no_title_detected'
    return title.text

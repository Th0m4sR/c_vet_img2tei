from lxml import etree
import re
from ..hocr_tools.hocr_helpers import build_ocr_carea_text, get_element_bbox
from ..constants import NAMESPACES
from pipeline.pipeline_logger import file_logger


def remove_first_element_and_return_text(hocr_tree: etree.ElementTree):
    """
    Removes the first ocr_carea element from an hOCR tree and returns its text (vertical axis is considered)
    :param hocr_tree: hOCR tree to remove first element of
    :return: text of the remove hOCR element
    """
    # Get the element that contains the title
    first_page = hocr_tree.xpath(".//x:div[@class='ocr_page']", namespaces=NAMESPACES)[0]
    first_page_careas = first_page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    first_page_careas.sort(key=lambda x: get_element_bbox(x)[1])
    first_element = first_page_careas[0]
    # Detach it from its parent
    parent = first_element.getparent()
    if parent is not None:
        parent.remove(first_element)
    # Return the contained text
    return build_ocr_carea_text(first_element)


def remove_last_element_and_return_text(hocr_tree: etree.ElementTree):
    """
    Removes the last ocr_carea element from an hOCR tree and returns its text (vertical axis is considered)
    :param hocr_tree: hOCR tree to remove last element of
    :return: text of the remove hOCR element
    """
    # Get the element that contains the title
    last_page_careas = hocr_tree.xpath(".//x:div[@class='ocr_page']", namespaces=NAMESPACES)[-1].xpath(
        ".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    last_page_careas.sort(key=lambda x: get_element_bbox(x)[1])
    last_element = last_page_careas[-1]
    # Detach it from its parent
    parent = last_element.getparent()
    if parent is not None:
        parent.remove(last_element)
    # Return the contained text
    return build_ocr_carea_text(last_element)


def build_tei_header(hocr_tree: etree.ElementTree,
                     document_title=None,
                     document_city=None,
                     document_author_name=None,
                     document_author_organization=None,
                     logger=None):
    # TODO Manchmal mehrere Minister
    """
    Build the teiHeader of a TEI XML document containing:
    - title (Verordnung ...)
    - release date (Vom XX. MONAT JAHR)
    - publishing city (STADT, den XX. MONAT JAHR)
    - responsible person for the text (Der Bundesminister für ZUSTÄNDIGKEIT <NAME / In Vertretung NAME>)
    and remove the elements containing this information from the regulation
    :param hocr_tree: hOCR tree without non-regulation-correlated elements and headers
    :param document_author_organization:
    :param document_author_name:
    :param document_city:
    :param document_title:
    :param logger: logger that is used to log the output
    :return: teiHeader element for the TEI XML file
    """
    # Set up logger
    if logger is None:
        logger = file_logger()

    # Root
    tei_header = etree.Element("teiHeader")

    # Metainformation
    file_desc = etree.Element("fileDesc")

    # Title Statement
    title_stmt = etree.Element("titleStmt")
    # - Title
    title = etree.Element("title")
    if document_title is None:
        title.text = '\n'.join(remove_first_element_and_return_text(hocr_tree))
    else:
        title.text = document_title
    """
    Der Bundesminister
    für ZUSTÄNDIGKEIT
    (In Vertretung)
    NAME
    """
    # - Author
    author = etree.Element("author")

    author_pattern_text = r'Der\s*Bundesminis[ftl]er\s*(.*?)(?: In\s*Vertretung|$)'
    authorin_pattern_text = r'Die\s*Bundesminis[ftl]erin\s*(.*?)(?: In\s*Vertretung|$)'

    author_pattern = re.compile(author_pattern_text)
    authorin_pattern = re.compile(authorin_pattern_text)

    author_lines = remove_last_element_and_return_text(hocr_tree)
    author_text = " ".join(author_lines[:-1])
    # -- Person
    pers_name = etree.Element("persName")
    pers_name_text = author_lines[-1]
    if document_author_name is None:
        pers_name.text = pers_name_text
    else:
        pers_name.text = document_author_name
    # -- Organization
    logger.info(f"Author text: '{author_text}'")
    org_name = etree.Element("orgName")
    if author_pattern.match(author_text):
        org_name_text = "Bundesministerium " + re.search(author_pattern_text, author_text).group(1)
    elif authorin_pattern.match(author_text):
        org_name_text = "Bundesministerium " + re.search(authorin_pattern_text, author_text).group(1)
    else:
        org_name_text = ""
        logger.warn("Unable to detect author organization")

    if document_author_organization is None:
        org_name.text = org_name_text
    else:
        org_name.text = document_author_organization

    author.append(pers_name)
    author.append(org_name)

    title_stmt.append(title)
    title_stmt.append(author)

    # Publishing Information
    publication_stmt = etree.Element("publicationStmt")
    publisher = etree.Element("publisher")
    # - Publishing Place
    publ_place = etree.Element("pubPlace")
    """Stadt, den XX. MONAT JAHR"""
    publ_place_text = " ".join(remove_last_element_and_return_text(hocr_tree))
    if document_city is None:
        publ_place.text = publ_place_text.split(",")[0]
    else:
        publ_place.text = document_city
    # - Date
    date = etree.Element("date")
    """VOM XX. MONAT JAHR"""
    date.text = " ".join(" ".join(remove_first_element_and_return_text(hocr_tree)).split(" ")[1:])

    publication_stmt.append(publisher)
    publication_stmt.append(publ_place)
    publication_stmt.append(date)

    source_desc = etree.fromstring("<sourceDesc><p></p></sourceDesc>")

    file_desc.append(title_stmt)
    file_desc.append(publication_stmt)
    file_desc.append(source_desc)

    tei_header.append(file_desc)

    return tei_header

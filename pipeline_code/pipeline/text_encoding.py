from xml.sax.saxutils import escape
import lxml.etree as etree
import re
from typing import Tuple
from pytesseract import pytesseract
from pipeline.resegmentation.paragraph_splitting_y import split_ocr_careas_horizontally
from pipeline.resegmentation.paragraph_merging_x import merge_careas_on_x_axis_in_document_tree
from pipeline.hocr_tools.hocr_helpers import get_element_bbox, build_ocr_carea_text, combine_hocr_pages
from pipeline.tei_encoding.layout_extraction import get_header_elements, remove_pre_text_elements, \
    remove_empty_careas, get_body_and_appendix_tree
from pipeline.tei_encoding.metadata_extraction import build_tei_header
from pipeline.constants import NAMESPACES, TEMP_WORKSPACE_ROOT_DIR, TEI_NAMESPACE, EMPTY_TEI_HEADER
from pipeline.tei_encoding.table_processing.table_encoding import encode_table
from pipeline.pipeline_logger import file_logger


# These should be expandable to "FIRST_LEVEL_HEADLINE_PATTERN"
from .tei_encoding.ocr_tools import encode_carea_lines_as_p, re_ocr_carea


TEIL_PATTERN_1 = re.compile(r"^Teil\s*\d\s*$")  # Teil 1
TEIL_PATTERN_2 = re.compile(r"^\b\w+er\b\s*Teil\s*$")  # Erster Teil

ABSCHNITT_PATTERN_1 = re.compile(r"^Abschnitt\s*\d+$")  # Abschnitt N
ABSCHNITT_PATTERN_2 = re.compile(r"^\d+\.\s*Abschnitt\s*$")  # N. Abschnitt

PARAGRAPH_PATTERN = re.compile(r"^„*(§|5|8|S|s|&amp;|\$)*\s*\d+\s*$")  # § N

FIRST_LEVEL_SEGMENT_PATTERN = re.compile(r"^[\(\}\]]\d+[\)\}\]]")  # (N)
# SECOND_LEVEL_SEGMENT_PATTERN = re.compile(r"^\d*[\.\,]+\s")  # 1. OLD VERSION
# SECOND_LEVEL_SEGMENT_PATTERN = re.compile(r"^[\d\w]*(\.|,)\s")  # 1.  # NOT SO OLD VERSION
SECOND_LEVEL_SEGMENT_PATTERN = re.compile(r"^\d+\s?[\.,]\s?.*")  # 1.
THIRD_LEVEL_SEGMENT_PATTERN = re.compile(r"^[a-z]\s*[\]\)\}]\s")  # a)
FOURTH_LEVEL_SEGMENT_PATTERN = re.compile(r"^([a-z])\1{1}\s*[\]\)\}]\s")  # aa)
FIFTH_LEVEL_SEGMENT_PATTERN = re.compile(r"^([a-z])\1{2}\s*[\]\)\}]\s")  # aaa)
SIXTH_LEVEL_SEGMENT_PATTERN = re.compile(r"^([a-z])\1{3}\s*[\]\)\}]\s")  # aaaa)

APPENDIX_ABSCHNITT_PATTERN = re.compile("Abschnitt [A-Z]: ")
FIRST_LEVEL_APPENDIX_HEADLINE_PATTERN = re.compile(r"^I+.\s")
SECOND_LEVEL_APPENDIX_HEADLINE_PATTERN = re.compile(r"^[A-Z].\s")

INHALTSUEBERSICHT_UEBERSCHRIFT = "Inhaltsübersicht"
TOC_ELEMENT_PATTERN = re.compile(r"^„*(§|5|8|S|s|&amp;|\$)+\s*\d+[a-z]+\s*\b")

FOOTNOTE_PATTERN = re.compile(r"^\*+\)*\s*")


def encode_hocr_tree_in_tei(hocr_tree: etree.ElementTree, images, max_area_dist: int = 50, logger=None):
    # Set up the logger if it was None
    if logger is None:
        logger = file_logger()

    # Splitting muss vor den Headern passieren, weil manche Header mit der Zeile darunter erkannt wurden

    # Step 1: Split the ocr_carea elements
    try:
        split_ocr_careas_horizontally(hocr_tree)
        logger.info("Split careas horizontally")
    except Exception as e:
        logger.exception("Error splitting careas horizontally: %s", e, exc_info=True)

    # Step 2: Extract the page headers
    try:
        headers = [get_header_elements(page) for page in hocr_tree.xpath("//x:div[@class='ocr_page']",
                                                                         namespaces=NAMESPACES)]
        logger.info("Extracted headers")
    except Exception as e:
        headers = [[] for _ in range(len(hocr_tree.xpath("//x:div[@class='ocr_page']",
                                                         namespaces=NAMESPACES)))]
        logger.exception("Error extracting header elements: %s", e, exc_info=True)

    # Step 3: Remove any elements that do not belong to the regulation
    try:
        remove_pre_text_elements(hocr_tree, logger=logger)
        logger.info("Removed pre-text elements")
    except Exception as e:
        logger.exception("Error removing pre-text elements: %s", e, exc_info=True)

    # Step 4: Split body and appendix
    try:
        body_tree, appendix_tree = get_body_and_appendix_tree(hocr_tree)
        logger.info("Split body from appendix")
    except Exception as e:
        logger.exception("Unable to split body from appendix: %s", e, exc_info=True)
        raise ValueError("The document does not have the required form to be encoded")
    appendix_page_start_idx = len(body_tree.xpath("//x:div[@class='ocr_page']", namespaces=NAMESPACES))
    # Storing at which page index the appendix starts
    text_headers = headers[:appendix_page_start_idx]
    appendix_headers = headers[appendix_page_start_idx:]
    logger.info("Separated headers")

    # Step 5: Prepare the body for encoding
    # 5.1: Remove the lines that are in the image (regulations from the 70s have a line between text columns)
    try:
        pre_empty_area_removal_carea_count = len(body_tree.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES))
        remove_empty_careas(body_tree, images)
        post_empty_area_removal_carea_count = len(body_tree.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES))
        logger.info("Removed lines from image and hOCR")
        # Documents where a line was between the text columns often have worse results.
        # Therefore, some of the steps have to be applied again
        if post_empty_area_removal_carea_count < pre_empty_area_removal_carea_count:
            logger.info("Pre-text elements had to be removed")
            body_tree = combine_hocr_pages([etree.fromstring(bytes(pytesseract.run_and_get_output(image, 'hocr', 'deu', '--dpi 300', '--psm 3'), 'utf-8')) for image in images[:appendix_page_start_idx]])
            text_headers = [get_header_elements(page) for page in body_tree.xpath("//x:div[@class='ocr_page']", namespaces=NAMESPACES)]
            split_ocr_careas_horizontally(body_tree)
            remove_pre_text_elements(body_tree, logger=logger)
            remove_empty_careas(body_tree, images)
            # print(etree.tostring(body_tree, pretty_print=True, encoding='unicode'))
            # plot_hocr_bboxes(body_tree, hocr_input_image=images[0], page_idx=0, ocr_carea=True, ocr_line=True)
    except Exception as e:
        logger.exception("Error removing lines from the body tree: %s", e, exc_info=True)
    # 5.2: Re-merge the elements on the x-axis that were detected separately
    # Erweitern statt mergen in body (Dafür nur 2er-cluster machen)
    #  Dafür: minimales x1, maximales y1, maximales x2, minimales y2 aus den beiden clustern
    try:
        merge_careas_on_x_axis_in_document_tree(body_tree, max_area_dist=max_area_dist)
        logger.info("Merged careas in body-tree")
    except Exception as e:
        logger.exception("Error merging careas in body tree: %s", e, exc_info=True)
    # plot_hocr_bboxes(appendix_tree.xpath("//x:div[@class='ocr_page']", namespaces=NAMESPACES)[0], hocr_input_image=images[appendix_page_start_idx], ocr_carea=True, ocr_line=True, ocr_word=True)
    try:
        merge_careas_on_x_axis_in_document_tree(appendix_tree, max_area_dist=max_area_dist)
        logger.info("Merged careas in appendix-tree")
    except Exception as e:
        logger.exception("Error merging careas in appendix tree: %s", e, exc_info=True)

    # Step 6: Encode the teiHeader
    try:
        tei_header = build_tei_header(body_tree, logger=logger)  # The header is generated from information in the body
        logger.info("Header encoded")
    except Exception as e:
        logger.exception("Error encoding teiHeader: %s", e, exc_info=True)
        tei_header = etree.fromstring(EMPTY_TEI_HEADER)

    # Step 7: Encode the body
    try:
        encoded_body = encode_body_tree(body_tree, images, body_header_elements=text_headers, logger=logger)
        logger.info("Body encoded")
    except Exception as e:
        logger.exception("Error encoding body: %s", e, exc_info=True)
        encoded_body = etree.fromstring("<body/>")

    # Step 8: Encode the appendix
    try:
        encoded_appendix = encode_appendix_tree(appendix_tree, images[appendix_page_start_idx:],
                                                num_body_pages=appendix_page_start_idx,
                                                appendix_header_elements=appendix_headers,
                                                logger=logger)
        logger.info("Appendix encoded")
    except Exception as e:
        logger.exception("Error encoding appendix: %s", e, exc_info=True)
        encoded_appendix = etree.fromstring("<back/>")

    tei_elem = etree.Element("TEI", version="3.3.0", xmlns=TEI_NAMESPACE)
    tei_elem.append(tei_header)
    text_elem = etree.Element("text")
    text_elem.append(encoded_body)
    text_elem.append(encoded_appendix)
    tei_elem.append(text_elem)
    tei_tree = etree.ElementTree(tei_elem)
    return tei_tree


def sanitize_line(line: str):
    """
    Takes a line and removes all special characters that are not * or . up to the first character
    :param line:
    :return:
    """
    pattern = re.compile(r'^[^a-zA-Z0-9*(.,$&§]*')
    modified_string = re.sub(pattern, '', line)
    return modified_string.strip()


def encode_body_tree(hocr_body_tree: etree.ElementTree, images,  # : List[Image],
                     bbox_margins: Tuple[int, int, int, int] = (20, 5, 5, 5),
                     body_header_elements=None,
                     logger=None) -> etree.ElementTree:
    if logger is None:
        logger = file_logger(None)
    body = etree.Element("body")
    current_teil = None
    current_abschnitt = None  # etree.SubElement(body, "div")  # Abschnitt 1
    current_paragraph = etree.SubElement(body, "div")  # § 1
    current_paragraph.attrib.update({"n": "0", "type": "preamble"})
    # ... as well as the subsegments of the paragraphs
    current_first_level_segment = None  # (1)
    # These two attributes will be global...
    teil_number = 1
    abschnitt_number = 1
    paragraph_number = 1
    # ... whereas these attributes will only be local in each paragraph
    first_level_segment_number = 1
    second_level_segment_number = 1
    third_level_segment_number = 1
    fourth_level_segment_number = 1
    fifth_level_segment_number = 1
    sixth_level_segment_number = 1
    # These are local enumerations that need to be reset as well after each start of a new element of the first
    #  enumeration or alternatively when a new subparagraph starts
    current_second_level_list = None  # This is a list / enumeration "1."
    current_second_level_item = None  # This is an item of the list / enumeration "1."
    current_third_level_list = None  # This is a list / enumeration "a)"
    current_third_level_item = None  # This is an item of the list / enumeration "a)"
    current_fourth_level_list = None  # This is a list / enumeration "aa)"
    current_fourth_level_item = None  # This is an item of the list / enumeration "aa)"
    current_fifth_level_list = None  # This is a list / enumeration "aaa)"
    current_fifth_level_item = None  # This is an item of the list / enumeration "aaa)"
    current_sixth_level_list = None  # This is a list / enumeration "aaaa)"

    # Used to track the table of contents
    encode_toc = False

    toc_teil = None
    toc_abschnitt = None
    toc_element = None

    toc_list = None
    toc_list_teil = None
    toc_list_abschnitt = None

    toc_teil_element_number = 1
    toc_abschnitt_element_number = 1
    toc_element_number = 1

    pages = hocr_body_tree.xpath("///x:body/x:div[@class='ocr_page']", namespaces=NAMESPACES)

    for page_idx in range(len(pages)):
        logger.info(f"Encoding body's page {page_idx}")
        page = pages[page_idx]
        page_image = images[page_idx]
        page_careas = page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)

        page_bbox = tuple(map(int, page.attrib['title'].split(";")[1].strip().split(" ")[1:]))

        # Initializing the first elements
        page_img = page.attrib['title'].split(";")[0].replace("\"", "\'").replace(TEMP_WORKSPACE_ROOT_DIR, '').replace('scantailor', 'images').replace('tif', 'png')  # TODO: Hier irgendwie den Server-Pfad berücksichtigen
        pb_string = f'<pb n="{page_idx + 1}" facs="{page_img}" ed="ausbildungsordnung" />'
        page_beginning = etree.fromstring(pb_string)

        # body.append(page_beginning)  # Relevant für spätere Iterationen
        if current_paragraph is not None:
            current_paragraph.append(page_beginning)
        elif current_abschnitt is not None:
            current_abschnitt.append(page_beginning)
        elif current_teil is not None:
            current_teil.append(page_beginning)
        else:
            body.append(page_beginning)

        if body_header_elements is not None:
            for header in body_header_elements[page_idx]:
                header_lines = " ".join(build_ocr_carea_text(header))
                # print(f"BODY HEADER LINES: {header_lines}")
                page_header = etree.fromstring(f'<fw type="head" place="top">{escape(header_lines.strip())}</fw>')
                body.append(page_header)
            # print(f"HEADER: {header_lines}")

        carea_idx = 0
        while carea_idx < len(page_careas):
            carea = page_careas[carea_idx]
            # Re-OCR the carea with the page segmentation mode that detects a uniform block of text
            carea_lines = [sanitize_line(line) for line in re_ocr_carea(page_bbox, page_image, carea, bbox_margins)]
            if len(carea_lines) == 0:
                carea_idx += 1
                continue
            # print("--------------------------------------------")
            # print(f"Page: {page_idx} - Carea: {carea_idx}")  # Zum Testen
            # print('\n'.join(carea_lines))

            # -------------------------- Start to try ----------------------------
            try:

                # DETECTING THE TABLE OF CONTENTS
                if carea_lines[0] == INHALTSUEBERSICHT_UEBERSCHRIFT:
                    logger.info("Starting to encode TOC")
                    toc_element = etree.Element("div")
                    toc_element.attrib.update({"type": "contents"})
                    toc_headline = etree.fromstring(f"<head>{INHALTSUEBERSICHT_UEBERSCHRIFT}</head>")
                    toc_element.append(toc_headline)
                    toc_list = etree.Element("list")
                    toc_element.append(toc_list)
                    encode_toc = True

                elif FOOTNOTE_PATTERN.match(carea_lines[0]):
                    logger.info(f"Encoded a footnote on body page {page_idx}")
                    footnote_text_lines = encode_carea_lines_as_p(re_ocr_carea(page_bbox, page_image,
                                                                               page_careas[carea_idx], bbox_margins))
                    footnote_element = etree.fromstring('<note type="footnote"></note>')
                    footnote_element.append(footnote_text_lines)
                    page_beginning.addnext(footnote_element)

                # THIS IS TO DETECT PARAGRAPH ELEMENTS IN THE TOC AS DETECTING THE TOC ELEMENTS WHICH ARE ABSCHNITTE
                #  ARE DONE IN THE SAME PART AS THE HEADLINES WHEN COMPARING THE ABSCHNITT_PATTERN_1
                elif encode_toc:
                    # Check if this is still part of the table of contents

                    next_carea = page_careas[carea_idx + 2] if carea_idx + 2 < len(page_careas) else pages[page_idx+1].xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)[0]
                    next_carea_image = page_image if len(page_careas) >= carea_idx+2 else images[page_idx+1]
                    next_text_lines = re_ocr_carea(page_bbox, next_carea_image, next_carea, bbox_margins)

                    # Check if this carea still belongs to the table of contents
                    if (TEIL_PATTERN_1.match(carea_lines[0]) and PARAGRAPH_PATTERN.match(next_text_lines[0])) or \
                            (TEIL_PATTERN_2.match(carea_lines[0]) and PARAGRAPH_PATTERN.match(next_text_lines[0])) or \
                            (ABSCHNITT_PATTERN_1.match(carea_lines[0]) and PARAGRAPH_PATTERN.match(next_text_lines[0])) or \
                            (ABSCHNITT_PATTERN_2.match(carea_lines[0]) and PARAGRAPH_PATTERN.match(next_text_lines[0])) or \
                            carea_lines[0].startswith('Auf Grund des') or \
                            PARAGRAPH_PATTERN.match(carea_lines[0]):
                        logger.info("Finished encoding TOC")
                        encode_toc = False
                        body.append(toc_element)
                        continue
                        # print(etree.tostring(toc_element, pretty_print=True, encoding='unicode'))
                        # print(f"Next Element: {carea_lines}")

                    # These are the same criteria as for a new section in the text
                    if TEIL_PATTERN_1.match(carea_lines[0]) or TEIL_PATTERN_2.match(carea_lines[0]):
                        teil_number_str = '<lb />\n'.join(carea_lines)
                        next_text_lines = re_ocr_carea(page_bbox, page_image, page_careas[carea_idx + 1], bbox_margins)
                        teil_headline = '<lb />\n'.join(next_text_lines)
                        toc_teil = etree.fromstring(f'<item n="{toc_teil_element_number}"><p>{str(teil_number_str)}<lb />{teil_headline}</p></item>')
                        toc_teil_element_number += 1
                        toc_list.append(toc_teil)
                        toc_list_teil = None
                        toc_list_abschnitt = None
                        toc_abschnitt = None
                        carea_idx += 2
                        continue
                    elif ABSCHNITT_PATTERN_1.match(carea_lines[0]) or ABSCHNITT_PATTERN_2.match(carea_lines[0]):
                        abschnitt_number_str = '<lb />\n'.join(carea_lines)
                        next_text_lines = re_ocr_carea(page_bbox, page_image, page_careas[carea_idx + 1], bbox_margins)
                        abschnitt_headline = '<lb />\n'.join(next_text_lines)
                        toc_abschnitt = etree.fromstring(f'<item n="{toc_abschnitt_element_number}"><p>{str(abschnitt_number_str)}<lb />{abschnitt_headline}</p></item>')
                        toc_abschnitt_element_number += 1
                        if toc_teil is not None:
                            if toc_list_teil is None:
                                toc_list_teil = etree.SubElement(toc_teil, "list")
                            toc_list_teil.append(toc_abschnitt)
                        else:
                            toc_list.append(toc_abschnitt)
                        toc_list_abschnitt = None
                        carea_idx += 2
                        continue
                    else:
                        toc_line_element_headline = '<lb/>\n'.join([escape(line) for line in carea_lines])
                        toc_line_element = etree.fromstring(
                            f'<item n="{toc_element_number}"><p>{toc_line_element_headline}</p></item>')
                        toc_element_number += 1
                        if toc_abschnitt is not None:
                            if toc_list_abschnitt is None:
                                toc_list_abschnitt = etree.SubElement(toc_abschnitt, "list")
                            toc_list_abschnitt.append(toc_line_element)
                        elif toc_teil is not None:
                            if toc_list_teil is None:
                                toc_list_teil = etree.SubElement(toc_teil, "list")
                            toc_list_teil.append(toc_line_element)
                        else:
                            toc_list.append(toc_line_element)

                # DETECTING HEADLINES
                elif TEIL_PATTERN_1.match(carea_lines[0]) or TEIL_PATTERN_2.match(carea_lines[0]):
                    logger.info(f"Started new Teil on page {page_idx}: {carea_lines}")
                    # Check if the preamble was added
                    if current_paragraph is not None and current_paragraph.attrib.get('type', '') == "preamble":
                        body.append(current_paragraph)
                        current_paragraph = None
                    current_teil = etree.SubElement(body, "div")
                    current_teil.attrib.update({"n": f"{str(teil_number)}", "type": "teil"})
                    teil_number += 1
                    # If a teil was detected, this element is "Abschnitt N"
                    #  and the next element is, e.g., Gegenstand, Dauer und Gliederung der Berufsausbildung.
                    #  This will be used to build <head> - elements and update the counter variable.
                    #  The same thing happens when a paragraph was detected
                    teil_number_str = '<lb />\n'.join(carea_lines)
                    next_text_lines = re_ocr_carea(page_bbox, page_image, page_careas[carea_idx + 1], bbox_margins)
                    teil_headline = '<lb />\n'.join(next_text_lines)
                    head_element = etree.fromstring(f'<head>{str(teil_number_str)}<lb />{teil_headline}</head>')
                    current_second_level_list = None
                    current_third_level_list = None
                    current_fourth_level_list = None  # This is a list / enumeration "aa)"
                    current_fifth_level_list = None  # This is a list / enumeration "aaa)"
                    current_sixth_level_list = None  # This is a list / enumeration "aaaa)"
                    current_teil.append(head_element)
                    carea_idx += 2

                elif ABSCHNITT_PATTERN_1.match(carea_lines[0]) or ABSCHNITT_PATTERN_2.match(carea_lines[0]):
                    logger.info(f"Started new Abschnitt on page {page_idx}: {carea_lines}")
                    # Check if the preamble was added
                    if current_paragraph is not None and current_paragraph.attrib.get('type', '') == "preamble":
                        body.append(current_paragraph)
                        current_paragraph = None
                    # Create the new abschnitt that is immediately appended
                    if current_teil is not None:
                        current_abschnitt = etree.SubElement(current_teil, "div")
                    else:
                        current_abschnitt = etree.SubElement(body, "div")
                    current_abschnitt.attrib.update({"n": f"{str(abschnitt_number)}", "type": "abschnitt"})
                    abschnitt_number += 1
                    # If an Abschnitt was detected, this element is "Abschnitt N"
                    #  and the next element is, e.g., Gegenstand, Dauer und Gliederung der Berufsausbildung.
                    #  This will be used to build <head> - elements and update the counter variable.
                    #  The same thing happens when a paragraph was detected
                    abschnitt_number_str = '<lb />\n'.join(carea_lines)
                    next_text_lines = re_ocr_carea(page_bbox, page_image, page_careas[carea_idx+1], bbox_margins)
                    abschnitt_headline = '<lb />\n'.join(next_text_lines)
                    head_element = etree.fromstring(f'<head>{str(abschnitt_number_str)}<lb />{abschnitt_headline}</head>')
                    current_second_level_list = None
                    current_third_level_list = None
                    current_fourth_level_list = None  # This is a list / enumeration "aa)"
                    current_fifth_level_list = None  # This is a list / enumeration "aaa)"
                    current_sixth_level_list = None  # This is a list / enumeration "aaaa)"
                    current_abschnitt.append(head_element)
                    carea_idx += 2
                    continue  # Continue to not update i another time in the end of the loop

                elif PARAGRAPH_PATTERN.match(carea_lines[0]):
                    logger.info(f"Started new Paragraph on page {page_idx}: {carea_lines}")
                    # print(f"{carea_lines[0]} matched {PARAGRAPH_PATTERN}")
                    if current_abschnitt is not None:  # and current_paragraph is not None:
                        current_paragraph = etree.SubElement(current_abschnitt, "div")
                    elif current_teil is not None:  # and current_paragraph is not None:
                        current_paragraph = etree.SubElement(current_teil, "div")
                    else:
                        current_paragraph = etree.SubElement(body, "div")
                    # current_paragraph = etree.SubElement(body, "div")
                    current_paragraph.attrib.update({"n": f"{str(paragraph_number)}", "type": "paragraph"})
                    paragraph_number += 1
                    # Reset local variables that only count in a paragraph
                    first_level_segment_number = 1
                    second_level_segment_number = 1
                    third_level_segment_number = 1
                    fourth_level_segment_number = 1
                    fifth_level_segment_number = 1
                    sixth_level_segment_number = 1
                    # Resetting current enumerations
                    current_second_level_list = None
                    current_third_level_list = None
                    current_fourth_level_list = None  # This is a list / enumeration "aa)"
                    current_fifth_level_list = None  # This is a list / enumeration "aaa)"
                    current_sixth_level_list = None  # This is a list / enumeration "aaaa)"
                    # Now the same thing as for <head> - elements in Abschnitte happens for paragraphs:
                    paragraph_number_str = '<lb />\n'.join(carea_lines)
                    next_text_lines = re_ocr_carea(page_bbox, page_image, page_careas[carea_idx+1], bbox_margins) if carea_idx+1 < len(page_careas) else []
                    paragraph_headline = '<lb />\n'.join([escape(line.strip()) for line in next_text_lines])
                    head_element = etree.fromstring(f'<head>{escape(paragraph_number_str.strip())}<lb />{paragraph_headline}</head>')
                    current_paragraph.append(head_element)
                    carea_idx += 2
                    continue  # Continue to not update i another time in the end of the loop

                # DETECTING TEXT SEGMENTS
                # Check if a new subparagraph starts (1)
                elif FIRST_LEVEL_SEGMENT_PATTERN.match(carea_lines[0]):
                    # Text elements will always be in a  <p>
                    new_text_element = encode_carea_lines_as_p(carea_lines)
                    if current_paragraph is not None:
                        current_first_level_segment = etree.SubElement(current_paragraph, "div")
                    elif current_abschnitt is not None:
                        current_first_level_segment = etree.SubElement(current_abschnitt, "div")
                    elif current_teil is not None:
                        current_first_level_segment = etree.SubElement(current_teil, "div")
                    else:
                        logger.exception(f"Was unable to append first level segment to any parent: {carea_lines}")
                    current_first_level_segment.attrib.update({"n": str(first_level_segment_number), "type": "section"})  # , "text_level": "1"
                    # Once the div is there, insert the text
                    current_first_level_segment.append(new_text_element)
                    first_level_segment_number += 1
                    # Resetting current enumerations
                    current_second_level_list = None
                    current_third_level_list = None
                    current_fourth_level_list = None
                    current_fifth_level_list = None
                    current_sixth_level_list = None
                    second_level_segment_number = 1
                    third_level_segment_number = 1
                    fourth_level_segment_number = 1
                    fifth_level_segment_number = 1
                    sixth_level_segment_number = 1
                elif SECOND_LEVEL_SEGMENT_PATTERN.match(carea_lines[0]):
                    # Text elements will always be in a  <p>
                    new_text_element = encode_carea_lines_as_p(carea_lines)
                    if current_first_level_segment is None:  # Check if the parent element is present
                        raise ValueError(f'No parent was found for second level segment: {" ".join(carea_lines)}')
                    if current_second_level_list is None:
                        current_second_level_list = etree.SubElement(current_first_level_segment, "list")
                    current_second_level_item = etree.SubElement(current_second_level_list, "item")
                    current_second_level_item.attrib.update({"n": str(second_level_segment_number)})  # , "text_level": "2"
                    # Once the list item is there, insert the text
                    current_second_level_item.append(new_text_element)
                    second_level_segment_number += 1
                    # Resetting current subenumeration
                    current_third_level_list = None
                    current_fourth_level_list = None
                    current_fifth_level_list = None
                    current_sixth_level_list = None
                    third_level_segment_number = 1
                    fourth_level_segment_number = 1
                    fifth_level_segment_number = 1
                    sixth_level_segment_number = 1
                elif THIRD_LEVEL_SEGMENT_PATTERN.match(carea_lines[0]):
                    # Text elements will always be in a  <p>
                    new_text_element = encode_carea_lines_as_p(carea_lines)
                    if current_second_level_item is None:  # Check if a parent is present
                        raise ValueError(f'No parent was found for third level segment: {" ".join(carea_lines)}')
                    if current_third_level_list is None:  # If this is the first element for this list, initialize the list
                        current_third_level_list = etree.SubElement(current_second_level_item, "list")
                    current_third_level_item = etree.SubElement(current_third_level_list, "item")
                    current_third_level_item.attrib.update({"n": str(third_level_segment_number)})  # , "text_level": "3"
                    # Once the list item is there, insert the text
                    current_third_level_item.append(new_text_element)
                    current_fourth_level_list = None
                    current_fifth_level_list = None
                    current_sixth_level_list = None
                    third_level_segment_number += 1
                    fourth_level_segment_number = 1
                    fifth_level_segment_number = 1
                    sixth_level_segment_number = 1
                elif FOURTH_LEVEL_SEGMENT_PATTERN.match(carea_lines[0]):
                    # Text elements will always be in a  <p>
                    new_text_element = encode_carea_lines_as_p(carea_lines)
                    if current_third_level_item is None:  # Check if a parent is present
                        raise ValueError(f'No parent was found for fourth level segment: {" ".join(carea_lines)}')
                    if current_fourth_level_list is None:  # If this is the first element for this list, initialize the list
                        current_fourth_level_list = etree.SubElement(current_third_level_item, "list")
                    current_fourth_level_item = etree.SubElement(current_fourth_level_list, "item")
                    current_fourth_level_item.attrib.update({"n": str(fourth_level_segment_number)})  # , "text_level": "4"
                    # Once the list item is there, insert the text
                    current_fourth_level_item.append(new_text_element)
                    current_fifth_level_list = None
                    current_sixth_level_list = None
                    fourth_level_segment_number += 1
                    fifth_level_segment_number = 1
                    sixth_level_segment_number = 1
                elif FIFTH_LEVEL_SEGMENT_PATTERN.match(carea_lines[0]):
                    # Text elements will always be in a  <p>
                    new_text_element = encode_carea_lines_as_p(carea_lines)
                    if current_fourth_level_item is None:  # Check if a parent is present
                        raise ValueError(f'No parent was found for fifth level segment: {" ".join(carea_lines)}')
                    if current_fifth_level_list is None:  # If this is the first element for this list, initialize the list
                        current_fifth_level_list = etree.SubElement(current_fourth_level_item, "list")
                    current_fifth_level_item = etree.SubElement(current_fifth_level_list, "item")
                    current_fifth_level_item.attrib.update({"n": str(fifth_level_segment_number)})  # , "text_level": "5"
                    # Once the list item is there, insert the text
                    current_fifth_level_item.append(new_text_element)
                    current_sixth_level_list = None
                    fifth_level_segment_number += 1
                    sixth_level_segment_number = 1
                elif SIXTH_LEVEL_SEGMENT_PATTERN.match(carea_lines[0]):
                    # Text elements will always be in a  <p>
                    new_text_element = encode_carea_lines_as_p(carea_lines)
                    if current_fifth_level_item is None:  # Check if a parent is present
                        raise ValueError(f'No parent was found for sixth level segment: {" ".join(carea_lines)}')
                    if current_sixth_level_list is None:  # If this is the first element for this list, initialize the list
                        current_sixth_level_list = etree.SubElement(current_fifth_level_item, "list")
                    current_sixth_level_item = etree.SubElement(current_sixth_level_list, "item")
                    current_sixth_level_item.attrib.update({"n": str(sixth_level_segment_number)})  # , "text_level": "6"
                    # Once the list item is there, insert the text
                    current_sixth_level_item.append(new_text_element)
                    sixth_level_segment_number += 1
                else:
                    # Text elements will always be in a <p>
                    new_text_element = encode_carea_lines_as_p(carea_lines)
                    # Each element must be at least a first level segment even it is not enumerated
                    if current_paragraph is not None:
                        current_first_level_segment = etree.SubElement(current_paragraph, "div")
                    elif current_abschnitt is not None:
                        current_first_level_segment = etree.SubElement(current_abschnitt, "div")
                    # Das hier dürfte eigentlich nicht möglich sein...
                    else:
                        current_first_level_segment = etree.SubElement(current_teil, "div")
                    current_first_level_segment.attrib.update({"type": "section"})  # , "text_level": "1"
                    # Once the div is there, insert the text
                    current_first_level_segment.append(new_text_element)
                    current_second_level_list = None
                carea_idx += 1
            except Exception as e:
                logger.exception("Error encoding body, continuing with next element: %s", e, exc_info=True)
                carea_idx += 1
    return body  # tei_tree


def encode_appendix_tree(hocr_appendix_tree: etree.ElementTree, images, num_body_pages: int = 0,
                         bbox_margins: Tuple[int, int, int, int] = (20, 5, 5, 5),
                         appendix_header_elements=None,
                         logger=None) -> etree.ElementTree:
    """
    Encodes the appendix
    Assumptions:
    - At most one table per page
    - Tables has lines that span up bounding boxes and all lines were at least in parts detected
    :param hocr_appendix_tree:
    :param images:
    :param num_body_pages: number of pages the body of the regulation has
    :param bbox_margins:
    :param appendix_header_elements:
    :param logger: Logger that is used to log
    :return:
    """
    if logger is None:
        logger = file_logger()
    # TODO: Anhang-Überschriften usw.
    back = etree.Element("back")
    pages = hocr_appendix_tree.xpath("//x:div[@class='ocr_page']", namespaces=NAMESPACES)

    for page_idx in range(len(pages)):
        logger.info(f"Encoding appendix page {page_idx}")
        page = pages[page_idx]
        page_image = images[page_idx]
        # plot_hocr_bboxes(page, page_image, page_idx=page_idx, ocr_carea=True, ocr_line=True, ocr_word=True)

        page_beginning = etree.fromstring(f'<pb n="{page_idx+num_body_pages+1}" />')

        back.append(page_beginning)
        if appendix_header_elements is not None:
            for header in appendix_header_elements[page_idx]:
                header_lines = " ".join(build_ocr_carea_text(header))
                page_header = etree.fromstring(f'<fw type="head" place="top">{escape(header_lines.strip())}</fw>')
                back.append(page_header)

        table, table_area = encode_table(ocr_page_element=page, ocr_page_image=page_image)
        if any([coordinate is None for coordinate in table_area]):
            table_was_appended = True
            logger.info(f"No table detected on appendix page {page_idx}")
        else:
            logger.info(f"Table detected on appendix page {page_idx}")
            table_was_appended = False
        table_y1 = table_area[1]
        table_y2 = table_area[3]
        for carea in page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES):
            try:
                carea_bbox = get_element_bbox(carea)
                if table_was_appended or carea_bbox[3] < table_y1 or carea_bbox[1] > table_y2:
                    carea_lines = [sanitize_line(line) for line in re_ocr_carea(carea_bbox, page_image, carea, bbox_margins, psm=6)]
                    new_p = encode_carea_lines_as_p(carea_lines)
                    back.append(new_p)
                else:
                    back.append(table)
                    logger.info(f"Appended table to appendix page {page_idx}")
                    table_was_appended = True
            except Exception as e:
                logger.exception("Error encoding appendix, continuing with next element: %s", e, exc_info=True)
        if not table_was_appended:
            back.append(table)
            logger.info(f"Appended table to appendix page {page_idx}")
    return back

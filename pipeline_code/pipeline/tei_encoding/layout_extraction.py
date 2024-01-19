from lxml import etree
from PIL import Image
import os
from typing import List, Tuple
from copy import deepcopy
import numpy as np
import re

from pipeline.constants import NAMESPACES
from pipeline.hocr_tools.hocr_helpers import get_element_bbox, combine_hocr_pages, ocr_elements_overlap_horizontally, \
    get_surrounding_bbox, build_ocr_carea_text, remove_element_from_hocr_tree
from pipeline.hocr_tools.hocr_properties import carea_contains_only_header, ocr_element_is_centered, \
    ocr_word_is_empty, average_line_height_and_std, carea_has_average_line_height
from pipeline.pipeline_logger import file_logger


# DOCUMENT LEVEL
def remove_pre_text_elements(hocr_tree: etree.ElementTree,
                             logger=None):
    """
    Takes an hOCR ElementTree as input and removes any element before the title. The title is defined by these
    properties:
    - It was detected as ocr_header
    - It is centered in the text
    - It has close to average line height
    :param logger:
    :param hocr_tree:
    :return:
    """
    if logger is None:
        logger = file_logger()
    avg_l_h, std_l_h = average_line_height_and_std(hocr_tree)
    page_idx = 0
    removed_elements = 0
    for page in hocr_tree.xpath("///x:body/x:div[@class='ocr_page']", namespaces=NAMESPACES):
        page_idx += 1
        careas = hocr_tree.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
        for carea in careas:
            carea_lines = build_ocr_carea_text(carea)
            if len(carea_lines) >= 1 and carea_lines[0] == 'Verordnung' or \
                    (carea_contains_only_header(carea) and ocr_element_is_centered(carea, page)
                     and carea_has_average_line_height(carea, avg_l_h, std_l_h)):  #  and carea_lines[1].split(" ")[0] == 'über')
                logger.info(f"Stopped removing elements at page {page_idx} and removed {removed_elements} elements")
                logger.info(f"First lines of the document are now: {carea_lines}")
                return
            else:
                carea.getparent().remove(carea)
                removed_elements += 1


def remove_empty_careas(hocr_tree: etree.ElementTree,
                        images) -> etree.ElementTree:
    """
    Removes all careas that contain only the empty word from an hOCR tree.
    The area of the bounding box is whitened in the image
    :param hocr_tree: hOCR tree
    :param images: list of images of the pages
    :return:
    """
    pages = hocr_tree.xpath(".//x:div[@class='ocr_page']", namespaces=NAMESPACES)
    for page_idx in range(len(pages)):
        page = pages[page_idx]
        for carea in page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES):
            if all([ocr_word_is_empty(w) for w in carea.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)]):
                # Set all pixels in the image to white
                x1, y1, x2, y2 = get_element_bbox(carea)
                # Create a white image with the same size as the region to be blanked out
                width, height = x2 - x1, y2 - y1
                white_image = Image.new('RGB', (width, height), color='white')
                # Paste the white image onto the original image at the specified region
                images[page_idx].paste(white_image, (x1, y1, x2, y2))

                parent = carea.getparent()
                if parent is not None:
                    parent.remove(carea)

        for separator in page.xpath(".//x:div[@class='ocr_separator']", namespaces=NAMESPACES):
            x1, y1, x2, y2 = get_element_bbox(separator)
            # Create a white image with the same size as the region to be blanked out
            width, height = x2 - x1, y2 - y1
            white_image = Image.new('RGB', (width, height), color='white')
            # Paste the white image onto the original image at the specified region
            images[page_idx].paste(white_image, (x1, y1, x2, y2))
            # print(f"White Image to {(x1, y1, x2, y2)}")
            parent = separator.getparent()
            if parent is not None:
                parent.remove(separator)


def get_body_and_appendix_tree(hocr_tree: etree.ElementTree) -> Tuple[etree.ElementTree, etree.ElementTree]:
    """
    Takes the document hOCR tree and builds two new trees:
    - The main document
    - The appendix
    in the hOCR format
    :param hocr_tree: hOCR tree with all pages of a document
    :return: Body and Appendix hOCR trees
    """
    is_body = True

    hocr_tree_copy = deepcopy(hocr_tree)
    body_tree = deepcopy(hocr_tree)
    appendix_tree = deepcopy(hocr_tree)

    hocr_tree_copy_pages = hocr_tree_copy.xpath("///x:body/x:div[@class='ocr_page']", namespaces=NAMESPACES)
    body_pages = body_tree.xpath("///x:body/x:div[@class='ocr_page']", namespaces=NAMESPACES)
    appendix_pages = appendix_tree.xpath("///x:body/x:div[@class='ocr_page']", namespaces=NAMESPACES)

    split_author_pattern = re.compile(r'Der Bundesminis(f|t|l)er (.*?)')
    split_authorin_pattern = re.compile(r'Die Bundesminis(f|t|l)erin (.*?)')

    is_body = True
    for page_idx in range(len(hocr_tree_copy_pages)):
        page = hocr_tree_copy_pages[page_idx]
        ocr_careas = page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
        if is_body:
            remove_element_from_hocr_tree(appendix_pages[page_idx])
        else:
            remove_element_from_hocr_tree(body_pages[page_idx])
        for carea in ocr_careas:
            carea_lines = " ".join(build_ocr_carea_text(carea))
            if split_author_pattern.match(carea_lines) or split_authorin_pattern.match(carea_lines):
                is_body = False

    return body_tree, appendix_tree


# PAGE LEVEL
def get_header_elements(hocr_page: etree.ElementTree) -> List[etree.ElementTree]:
    """
    Detects header elements in an hocr page, removes them from the hOCR ElementTree and returns them in a list
    :param hocr_page: page element from which headers will be removed and returned
    :return: list of found headers on this page
    """
    ocr_careas = hocr_page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    sorted_ocr_careas = sorted(ocr_careas, key=lambda x: get_element_bbox(x)[1])
    headers = [sorted_ocr_careas[0]]
    sorted_ocr_careas[0].getparent().remove(sorted_ocr_careas[0])
    for carea in sorted_ocr_careas[1:]:
        if not ocr_elements_overlap_horizontally(headers[0], carea):
            break  # return headers
        headers.append(carea)
        carea.getparent().remove(carea)
    for header in headers:
        if all([ocr_word_is_empty(word) for word in header.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)]):
            headers.remove(header)

    headers.sort(key=lambda x: get_element_bbox(x)[0])
    combine_headers(headers)
    split_headers(headers)
    return headers


def combine_headers(sorted_headers: List[etree.ElementTree], max_line_dist: int = 40):
    """
    Takes the detected headers and merges them if they are closer than max_line_dist to each other
    :param sorted_headers:
    :param max_line_dist:
    :return:
    """
    header_idx = 1
    while header_idx < len(sorted_headers):
        left_bbox = get_element_bbox(sorted_headers[header_idx-1])
        right_bbox = get_element_bbox(sorted_headers[header_idx])
        left_x2 = left_bbox[2]
        reight_x1 = right_bbox[0]
        # Check if the bboxes overlap or are close enough to each other
        if np.abs(reight_x1 - left_x2) < max_line_dist or left_bbox[0] <= right_bbox[0] <= left_bbox[2] or right_bbox[0] <= left_bbox[0] <= right_bbox[2]:
            left_line = sorted_headers[header_idx-1].xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat' or @class='ocr_header']",
                                                           namespaces=NAMESPACES)[-1]
            for word in sorted_headers[header_idx].xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES):
                left_line.append(word)
            left_line[:] = sorted(left_line, key=lambda x: get_element_bbox(x)[0])
            x1, y1, x2, y2 = get_surrounding_bbox(left_line.xpath(".//x:span[@class='ocrx_word']",
                                                                  namespaces=NAMESPACES))
            left_line.set("title", f"bbox {x1} {y1} {x2} {y2}")
            sorted_headers[header_idx-1].set("title", f"bbox {x1} {y1} {x2} {y2}")
            sorted_headers.remove(sorted_headers[header_idx])
        else:
            header_idx += 1


def split_headers(sorted_headers: List[etree.ElementTree], max_word_dist: int = 100):
    """
    Takes the detected headers and splits them if they are further than max_line_dist to each other
    :param sorted_headers:
    :param max_word_dist:
    :return:
    """
    header_idx = 0
    while header_idx < len(sorted_headers):
        for word in sorted_headers[header_idx].xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES):
            if word.text is None:
                parent = word.getparent()
                if parent is not None:
                    parent.remove(word)
        header_words = sorted_headers[header_idx].xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)
        word_idx = 1
        while word_idx < len(header_words):
            left_bbox = get_element_bbox(header_words[word_idx-1])
            right_bbox = get_element_bbox(header_words[word_idx])
            lower_x2 = left_bbox[2]
            upper_x1 = right_bbox[0]
            if np.abs(upper_x1 - lower_x2) > max_word_dist and not left_bbox[0] <= right_bbox[0] <= left_bbox[2] and not right_bbox[0] <= left_bbox[0] <= right_bbox[2]:
                old_words = header_words[:word_idx]
                new_words = header_words[word_idx:]

                x1, y1, x2, y2 = get_surrounding_bbox(new_words)
                new_carea = etree.Element("{http://www.w3.org/1999/xhtml}div")
                new_carea.set("class", "ocr_carea")
                new_carea.set("title", f"bbox {x1} {y1} {x2} {y2}")
                new_p = etree.Element("{http://www.w3.org/1999/xhtml}p")
                new_p.set("class", "ocr_par")
                new_p.set("title", f"bbox {x1} {y1} {x2} {y2}")
                new_line = etree.Element("{http://www.w3.org/1999/xhtml}span")
                new_line.set("class", "ocr_line")
                new_line.set("title", f"bbox {x1} {y1} {x2} {y2}")
                for word in new_words:
                    new_line.append(word)
                new_p.append(new_line)
                new_carea.append(new_p)

                x1, y1, x2, y2 = get_surrounding_bbox(old_words)
                sorted_headers[header_idx].set("title", f"bbox {x1} {y1} {x2} {y2}")
                sorted_headers[header_idx].xpath(".//x:p[@class='ocr_par']",
                                                 namespaces=NAMESPACES)[-1].set("title", f"bbox {x1} {y1} {x2} {y2}")
                sorted_headers[header_idx].xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat' or @class='ocr_header']",
                                                 namespaces=NAMESPACES)[-1].set("title", f"bbox {x1} {y1} {x2} {y2}")

                sorted_headers.append(new_carea)
                sorted_headers.sort(key=lambda x: get_element_bbox(x)[0])
            word_idx += 1
        header_idx += 1

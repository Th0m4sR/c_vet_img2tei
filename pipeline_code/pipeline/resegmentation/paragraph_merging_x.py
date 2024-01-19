from lxml import etree
import numpy as np
from ..hocr_tools.hocr_properties import carea_contins_only_empty_words
from ..constants import NAMESPACES
from pipeline.hocr_tools.hocr_helpers import ocr_elements_overlap_horizontally, get_element_bbox, \
    remove_element_from_hocr_tree


# I will check for horizontally overlapping careas.
# If they are detected, the x1 values are compared.
# The element with the higher x1 value will be expanded to the lower x1 value.
# After all elements have been expanded, all left elements that were involved, are removed


def merge_careas_on_x_axis_in_document_tree(hocr_tree: etree.ElementTree, max_area_dist: float = 50):
    """
    For each page all careas witihn the same height that are at most max_area_dist apart are merged
    :param hocr_tree: ElementTree in which the careas are merged
    :param max_area_dist: maximum distance between two carea at the same height
    :return:
    """
    # TODO Funktion, um max_area_dist dynamisch zu berechnen
    pages = hocr_tree.xpath("///x:div[@class='ocr_page']", namespaces=NAMESPACES)
    merged_in_careas = []
    for page_idx in range(len(pages)):
        page = pages[page_idx]
        careas = page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
        careas.sort(key=lambda x: get_element_bbox(x)[0])
        for area in careas:
            for other_area in careas[careas.index(area) + 1:]:
                if ocr_elements_overlap_horizontally(area, other_area) and \
                        not carea_contins_only_empty_words(area) and \
                        not carea_contins_only_empty_words(other_area):
                    a_x1, a_y1, a_x2, a_y2 = get_element_bbox(area)
                    b_x1, b_y1, b_x2, b_y2 = get_element_bbox(other_area)
                    if a_x2 <= b_x2:
                        left_area = area
                        right_area = other_area
                    else:
                        left_area = other_area
                        right_area = area
                    area_distance = min([np.abs(a_x1 - b_x2), np.abs(a_x2 - b_x1)])
                    if area_distance < max_area_dist or a_x1 <= b_x1 <= a_x2 or b_x1 <= a_x1 <= b_x2 or \
                            a_x1 <= b_x2 <= a_x2 or b_x1 <= a_x2 <= b_x2:
                        left_bbox = get_element_bbox(left_area)
                        right_bbox = get_element_bbox(right_area)
                        x1 = min([a_x1, b_x1])
                        y1 = right_bbox[1]  # min([a_y1, b_y1])  # right_bbox[1]
                        x2 = max([a_x2, b_x2])
                        y2 = right_bbox[3]  # max([a_y2, b_y2])  # right_bbox[3]
                        right_area.set("title", f"bbox {x1} {y1} {x2} {y2}")
                        merged_in_careas.append(left_area)
    for area in merged_in_careas:
        remove_element_from_hocr_tree(area)

import string
from lxml import etree
import numpy as np
from pipeline.hocr_tools.hocr_helpers import get_element_bbox, remove_element_from_hocr_tree, \
    get_surrounding_bbox
from pipeline.constants import NAMESPACES
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pipeline.hocr_tools.hocr_properties import carea_contins_only_empty_words

# Die Tabelle geht von links nach rechts, dabei kann sich die Zeile an manchen Stellen aufteilen.
#  Die gefundenen Linien (Linien als leere ocr_par erkannt) können als Trennungen genutzt werden, um dann zu gucken,
#  was dazwischen liegt.
#  Alles, was oberhalb der ersten Linie liegt, kann als Text identifiziert werden
#  Tabellen können über mehrere Seiten gehen

"""
This module takes care of the extraction of the table structure from an hOCR ocr_carea element that contains all
information that was detected from an image
"""


def extract_page_table_boxes(ocr_page_element, ocr_page_image, plot_td_boxes: bool = False):
    # TODO Das hier in das appendix encoding integrieren
    # Detect table lines
    vlines, hlines = detect_table_lines(ocr_page_element, ocr_page_image)
    # Form the lines to boxes
    td_boxes = build_table_data_boxes(vlines, hlines)
    # Make the boxes fit around the content
    expand_td_boxes(ocr_page_element, td_boxes)
    # Remove the OCR elements that lie in the table as they are re-ocred anyways
    remove_ocr_elements_on_table(ocr_page_element, td_boxes)  # TODO Testen
    if plot_td_boxes:
        fig, ax = plt.subplots()
        fig.set_size_inches(ocr_page_image.width / 300, ocr_page_image.height / 300)
        ax.axis('off')
        ax.imshow(ocr_page_image)
        for row in td_boxes:
            for (x_lower, y_lower, x_upper, y_upper) in row:
                rectangle = patches.Polygon(
                    [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                    closed=True, edgecolor='green', linewidth=1, fill=False)
                fig.gca().add_patch(rectangle)
        for row in td_boxes:
            for (x_lower, y_lower, x_upper, y_upper) in row:
                rectangle = patches.Polygon(
                    [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                    closed=True, edgecolor='green', linewidth=1, fill=False)
                fig.gca().add_patch(rectangle)
        # fig.savefig('z_pipeline_plots/table_boxes', dpi=300, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.show()
    return td_boxes


def get_table_area_from_td_boxes(td_boxes):
    table_x1, table_y1, table_x2, table_y2 = (None, None, None, None)
    for table_line in td_boxes:
        for table_cell in table_line:
            if table_x1 is None or table_x1 > table_cell[0]:
                table_x1 = table_cell[0]
            if table_y1 is None or table_y1 > table_cell[1]:
                table_y1 = table_cell[1]
            if table_x2 is None or table_x2 < table_cell[2]:
                table_x2 = table_cell[2]
            if table_y2 is None or table_y2 < table_cell[3]:
                table_y2 = table_cell[3]
    return [table_x1, table_y1, table_x2, table_y2]


def remove_ocr_elements_on_table(ocr_page_element, td_boxes):
    """
    Removes all ocr elements of the ocr_page element that overlap with the td_boxes
    :param ocr_page_element:
    :param td_boxes:
    :return:
    """
    # TODO Testen
    table_area = get_table_area_from_td_boxes(td_boxes)
    # If no table was detected, i.e., the table area's coordinates are all None, do nothing
    if any([coordinate is None for coordinate in table_area]):
        return
    # TODO Zur Not einfach alle careas entfernen, die mit der table_area überlappen
    # Remove any word in the table
    for word in ocr_page_element.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES):
        word_bbox = get_element_bbox(word)
        if rectangles_overlap(word_bbox, table_area):
            remove_element_from_hocr_tree(word)
    # Remove any line with no word
    for line in ocr_page_element.xpath(".//x:span[@class='ocr_line']", namespaces=NAMESPACES):
        if len(line.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)) == 0:
            remove_element_from_hocr_tree(line)
    # Remove any ocr_carea without lines
    for carea in ocr_page_element.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES):
        if len(carea.xpath(".//x:span[@class='ocr_line']", namespaces=NAMESPACES)) == 0:
            remove_element_from_hocr_tree(carea)
    # Split the careas if the lines are far apart
    for carea in ocr_page_element.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES):
        lines = carea.xpath(".//x:span[@class='ocr_line']", namespaces=NAMESPACES)
        line_idx = 1
        while line_idx < len(lines):
            prev_line_bbox = get_element_bbox(lines[line_idx-1])
            line_bbox = get_element_bbox(lines[line_idx])
            if np.abs(line_bbox[1] - prev_line_bbox[3]) > 50:  # Parameter noch besser wählen
                new_carea = etree.Element("{http://www.w3.org/1999/xhtml}div")
                new_carea.set("class", "ocr_carea")
                new_p = etree.Element("{http://www.w3.org/1999/xhtml}p")
                new_p.set("class", "ocr_par")
                for line in lines[:line_idx]:
                    new_p.append(line)
                carea.addprevious(new_carea)
            line_idx += 1
    # Reshape the ocr_careas
    for carea in ocr_page_element.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES):
        x1, y1, x2, y2 = get_surrounding_bbox(carea.xpath(".//x:span[@class='ocr_line']", namespaces=NAMESPACES))
        carea.set("title", f"bbox {x1} {y1} {x2} {y2}")


def expand_td_boxes(ocr_page_element, initial_td_boxes):
    """
    Takes the td_boxes that were detected on the ocr_page_element and expands them until they do not overlap with any
    ocrx_word of the ocr_page_element
    :param ocr_page_element:
    :param initial_td_boxes:
    :return:
    """
    page_bbox = list(map(int, ocr_page_element.attrib.get('title').split(";")[1].strip().split(" ")[1:]))
    for table_line_idx in range(len(initial_td_boxes)):
        for table_cell_idx in range(len(initial_td_boxes[table_line_idx])):
            changed = True
            while changed:
                overlapping_words = get_td_box_overlapping_words(ocr_page_element, initial_td_boxes[table_line_idx][table_cell_idx])

                new_td_box = list(get_surrounding_bbox(overlapping_words)) if overlapping_words else initial_td_boxes[table_line_idx][table_cell_idx]

                x1 = min([new_td_box[0], initial_td_boxes[table_line_idx][table_cell_idx][0]])
                y1 = min([new_td_box[1], initial_td_boxes[table_line_idx][table_cell_idx][1]])
                x2 = max([new_td_box[2], initial_td_boxes[table_line_idx][table_cell_idx][2]])
                y2 = max([new_td_box[3], initial_td_boxes[table_line_idx][table_cell_idx][3]])

                new_td_box = [x1, y1, x2, y2]

                if new_td_box != initial_td_boxes[table_line_idx][table_cell_idx]:

                    new_x1, new_y1, new_x2, new_y2 = new_td_box

                    window_expansion = 5
                    new_x1 = max([new_x1-window_expansion, page_bbox[0]])
                    new_y1 = max([new_y1-window_expansion, page_bbox[1]])
                    new_x2 = min([new_x2+window_expansion, page_bbox[2]])
                    new_y2 = min([new_y2+window_expansion, page_bbox[3]])

                    new_td_box = [new_x1, new_y1, new_x2, new_y2]

                    initial_td_boxes[table_line_idx][table_cell_idx] = new_td_box
                    # Move the upper line of the table cell under this one to the lower line of this one to avoid
                    # duplicates in the table
                    # TODO Oder doch eher nicht?
                    if table_line_idx < len(initial_td_boxes) - 1:
                        initial_td_boxes[table_line_idx+1][table_cell_idx][1] = new_y2
                        # Make sure y2 >= y1 for the cell below
                        if new_y2 > initial_td_boxes[table_line_idx+1][table_cell_idx][3]:
                            initial_td_boxes[table_line_idx + 1][table_cell_idx][3] = new_y2
                            # TODO Tabellenzellen nochmal plotten?
                    changed = True
                else:
                    changed = False


def get_td_box_overlapping_words(ocr_page_element, td_box):
    word_bboxes = [word for word in ocr_page_element.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)
                   if rectangles_overlap(get_element_bbox(word), td_box)]
    return word_bboxes


def rectangles_overlap_horizontally(rect_1, rect_2):
    _, e1_y1, _, e1_y2 = rect_1
    _, e2_y1, _, e2_y2 = rect_2
    if e1_y1 <= e2_y1 <= e1_y2 or e1_y1 <= e2_y2 <= e1_y2 or e2_y1 <= e1_y1 <= e2_y2 or e2_y1 <= e1_y2 <= e2_y2:  # e1_y2 < e2_y1 or e2_y2 < e1_y1:
        return True
    return False


def rectangles_overlap_vertically(rect_1, rect_2):
    e1_x1, _, e1_x2, _ = rect_1
    e2_x1, _, e2_x2, _ = rect_2
    if e1_x2 < e2_x1 or e2_x2 < e1_x1:
        return False
    return True


def rectangles_overlap(rect_1, rect_2):
    return rectangles_overlap_horizontally(rect_1, rect_2) and rectangles_overlap_vertically(
        rect_1, rect_2)


def detect_table_lines(ocr_page_element, ocr_page_image, plot_table_lines: bool = False):
    """
    Finds all elements that represent table lines in the ocr_page_element and fills the corresponding areas in the
    ocr_page_image with white pixels to remove them
    :param ocr_page_element:
    :param ocr_page_image:
    :param plot_table_lines: If true, the detected lines are plotted onto the image
    :return: vlines and hlines where each line is determined from its start to end and the center of the other dimension
    """
    # TODO Was, wenn keine Zeilen erkannt wurden? -> Leere Liste
    # Lines will be considered to be all careas that have only empty words
    #  or div elements that are ocr_separators
    vlines = []
    hlines = []
    # print(ocr_page_element.attrib)
    # print(ocr_page_element.attrib.get('title').split(";")[1].strip().split(" "))
    page_bbox = list(map(int, ocr_page_element.attrib.get('title').split(";")[1].strip().split(" ")[1:]))
    for ocr_carea in ocr_page_element.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES):
        if carea_contins_only_empty_words(ocr_carea):
            # Get the element's bbox
            x1, y1, x2, y2 = get_element_bbox(ocr_carea)
            # Add the element to the line elements
            if x2-x1 > y2-y1:
                hlines.append([x1, y1 + (y2-y1)/2, x2, y1 + (y2-y1)/2])
            else:
                vlines.append([x1 + (x2-x1)/2, y1, x1 + (x2-x1)/2, y2])
            # Set all pixels in the image to white
            width, height = x2 - x1, y2 - y1
            white_image = Image.new('RGB', (width, height), color='white')
            ocr_page_image.paste(white_image, (x1, y1, x2, y2))
            # Remove the element from the hOCR tree
            remove_element_from_hocr_tree(ocr_carea)
    if len(vlines) == 0 or len(hlines) == 0:
        return [], []
    # TODO Separators
    # After all lines were detected, some dummy lines that build up the borders around the table are added...
    table_min_x = page_bbox[0]+5
    table_max_x = page_bbox[2]-5
    table_min_y = min([line[1] for line in hlines + vlines])
    table_max_y = max([line[3] for line in hlines + vlines])

    dummy_lower_vline = [table_min_x, table_min_y, table_min_x, table_max_y]
    dummy_upper_vline = [table_max_x, table_min_y, table_max_x, table_max_y]
    dummy_lower_hline = [table_min_x, table_min_y, table_max_x, table_min_y]
    dummy_upper_hline = [table_min_x, table_max_y, table_max_x, table_max_y]

    # ... and all table line are expanded to go through the entire table
    for hline in hlines:
        hline[0] = table_min_x
        hline[2] = table_max_x
    for vline in vlines:
        vline[1] = table_min_y
        vline[3] = table_max_y

    vlines.append(dummy_lower_vline)
    vlines.append(dummy_upper_vline)
    hlines.append(dummy_lower_hline)
    hlines.append(dummy_upper_hline)

    # Sort the vertical and horizontal lines
    vlines.sort(key=lambda x: x[0])
    hlines.sort(key=lambda x: x[1])

    # Do some noise filtering here
    # Remove falsely detected / too small careas
    remove_small_bboxes(ocr_page_element)  # TODO Still in Testing

    # Remove duplicate lines
    for line_set in [hlines, vlines]:
        line_counter = 0
        while line_counter < len(line_set):
            inner_counter = line_counter+1
            while inner_counter < len(line_set):
                if box_equivalence(line_set[line_counter], line_set[inner_counter]):
                    del line_set[inner_counter]
                    continue
                inner_counter += 1
            line_counter += 1

    if plot_table_lines:
        fig, ax = plt.subplots()
        # Assuming 300 DPI
        fig.set_size_inches(ocr_page_image.width / 300, ocr_page_image.height / 300)
        ax.axis('off')
        ax.imshow(ocr_page_image)
        for (x_lower, y_lower, x_upper, y_upper) in hlines+vlines:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='red', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
        for (x_lower, y_lower, x_upper, y_upper) in [get_element_bbox(carea) for carea in ocr_page_element.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)]:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='blue', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
        for (x_lower, y_lower, x_upper, y_upper) in [get_element_bbox(carea) for carea in ocr_page_element.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)]:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='green', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
        # fig.savefig('z_pipeline_plots/table_lines', dpi=300, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.show()
    return vlines, hlines


def remove_small_bboxes(ocr_page_element: etree.ElementTree, min_bbox_area: int = 3000):
    """
    Removes small ocr bboxes that are considered to be noise
    :param ocr_page_element:
    :param min_bbox_area:
    :return:
    """
    for carea in ocr_page_element.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES):
        x1, y1, x2, y2 = get_element_bbox(carea)
        if (x2-x1) * (y2-y1) < min_bbox_area:
            remove_element_from_hocr_tree(carea)


def build_table_data_boxes(vertical_lines, horizontal_lines):
    """
    Builds the table boxes from the sets of vertical and horizontal lines in the pattern:
    [
    [[x11], [x12], [x13]]
    [[x21], [x22], [x33]]
    [[x31], [x32], [x33]]
    ] where xij = x1, y1, x2, y2
    :param vertical_lines:
    :param horizontal_lines:
    :return:
    """
    table_boxes = []
    for i in range(1, len(horizontal_lines)):
        table_line = []
        prev_hor_y = horizontal_lines[i - 1][1]
        hor_y = horizontal_lines[i][1]
        for j in range(1, len(vertical_lines)):
            prev_ver_x = vertical_lines[j - 1][0]
            ver_x = vertical_lines[j][0]
            table_line.append([prev_ver_x, prev_hor_y, ver_x, hor_y])
        table_boxes.append(table_line)
    return table_boxes


def box_equivalence(box_1, box_2, pixel_threshold=10):
    """
    Checks if each coordinate of the input boxes differ by at most the pixel_threshold
    :param box_1: First box
    :param box_2: Second box
    :param pixel_threshold: The maximum difference between each coordinate
    :return: True if the boxes are similar, i.e. each coordinate of both boxes differs at most the pixel_threshold
    """
    return abs(box_1[0] - box_2[0]) < pixel_threshold and abs(box_1[1] - box_2[1]) < pixel_threshold and abs(box_1[2] - box_2[2]) < pixel_threshold and abs(box_1[3] - box_2[3]) < pixel_threshold


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------


def remove_words_on_table_lines(hocr_table_carea_element: etree.ElementTree, hlines, vlines,
                                coordinate_offset=(0, 0)):
    """
    Removes any ocr_carea div-element of the input hocr_table_carea_element that is:
    - Centered on one of the hlines or vlines
    - And overlaps by at most 30 pixels in both directions
    :param hocr_table_carea_element:
    :param hlines: horizontal lines of the table
    :param vlines: vertical lines of the table
    :param coordinate_offset: If the table was constructued from applying OCR on a cropped part of the image,
    the offset where the cropped image begins is necessary
    :return:
    """
    ocr_careas = hocr_table_carea_element.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    # TODO: In dem genutzten PSM sind alle Zeilen eine Textzeile -> Zu hohe Zeilen entfernen
    for carea in ocr_careas:
        carea_bbox = get_element_bbox(carea)
        carea_center_x = carea_bbox[0] + (carea_bbox[2] - carea_bbox[0]) / 2
        carea_center_y = carea_bbox[1] + (carea_bbox[3] - carea_bbox[1]) / 2
        for table_line in hlines:
            # Setting up the line coordinates from the first OCR-process to the re-ocr
            table_line[0] = table_line[0] - coordinate_offset[0]
            table_line[1] = table_line[1] - coordinate_offset[1]
            table_line[2] = table_line[2] - coordinate_offset[0]
            table_line[1] = table_line[1] - coordinate_offset[1]

            line_center = table_line[1] + (table_line[3] - table_line[1])/2
            # Box muss klein sein und mitten auf der Linie liegen
            if np.abs(carea_bbox[1] - table_line[1]) < 30 and np.abs(carea_bbox[3] - table_line[3]) < 30 and \
                    np.abs(line_center - carea_center_y) < 5:
                parent = carea.getparent()
                if parent is not None:
                    parent.remove(carea)

        for table_line in vlines:
            # Setting up the line coordinates from the first OCR-process to the re-ocr
            table_line[0] = table_line[0] - coordinate_offset[0]
            table_line[1] = table_line[1] - coordinate_offset[1]
            table_line[2] = table_line[2] - coordinate_offset[0]
            table_line[3] = table_line[3] - coordinate_offset[1]

            line_center = table_line[0] + (table_line[2] - table_line[0])/2
            # Box muss klein sein und mitten auf der Linie liegen
            if np.abs(carea_bbox[0] - table_line[0]) < 30 and np.abs(carea_bbox[2] - table_line[2]) < 30 and \
                    np.abs(line_center - carea_center_x) < 5:
                parent = carea.getparent()
                if parent is not None:
                    parent.remove(carea)


# Helper function to calculate horizontal overlap
def calculate_horizontal_overlap(bbox1, bbox2):
    """
    Computes the number of overlapping pixels on the x-axis between two bboxes
    :param bbox1: [x11, y11, x12, y12]
    :param bbox2: [x21, y21, x22, y22]
    :return: Overlapping distance of bbox1 and bbox2 on the x-axis
    """
    return max(0, min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0]))


# Helper function to calculate vertical overlap
def calculate_vertical_overlap(bbox1, bbox2):
    """
    Computes the number of overlapping pixels on the y-axis between two bboxes
    :param bbox1: [x11, y11, x12, y12]
    :param bbox2: [x21, y21, x22, y22]
    :return: Overlapping distance of bbox1 and bbox2 on the y-axis
    """
    return max(0, min(bbox1[3], bbox2[3]) - max(bbox1[1], bbox2[1]))


def calculate_overlap_percentage(rect1, rect2):
    """
    Calculates how much percent of two bboxes overlap
    :param rect1:
    :param rect2:
    :return: Overlapping area in percentage of rect1 and rect2
    """
    # Rectangles are represented as (x1, y1, x2, y2), where (x1, y1) is the bottom-left corner
    # and (x2, y2) is the top-right corner.
    # Calculate the coordinates of the overlapping region
    x1_overlap = max(rect1[0], rect2[0])
    y1_overlap = max(rect1[1], rect2[1])
    x2_overlap = min(rect1[2], rect2[2])
    y2_overlap = min(rect1[3], rect2[3])
    # Check if there is an overlap
    if x1_overlap < x2_overlap and y1_overlap < y2_overlap:
        # Calculate the area of overlap
        overlap_area = (x2_overlap - x1_overlap) * (y2_overlap - y1_overlap)
        # Calculate the area of both rectangles
        area_rect1 = (rect1[2] - rect1[0]) * (rect1[3] - rect1[1])
        area_rect2 = (rect2[2] - rect2[0]) * (rect2[3] - rect2[1])
        # Calculate the percentage of overlap
        overlap_percentage = (overlap_area / min(area_rect1, area_rect2)) * 100
        return overlap_percentage  # overlap_area
    else:
        # No overlap
        return 0


def extend_table_data_areas_to_content(hocr_table_re_ocred_tree: etree.ElementTree, td_boxes,
                                       coordinate_offset=(0, 0)):
    """
    Detects elements of the table data boxes that contain the same content and expands them to fit around their entire
    content
    :param hocr_table_re_ocred_tree: the re-OCR result of the image cropped to the table content
    :param td_boxes: The td_boxes that were found by expanding the table lines
    :param coordinate_offset: If the input image was cropped from the original, the offset needs to be considered
    :return:
    """
    # Für horizontale merges: Mindestlänge, die in rechtes / linkes Feld regen muss
    # Für vertikale merges: Prozentteil, der in unteres / oberes Feld ragen muss
    carea_elements = hocr_table_re_ocred_tree.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    merge_clusters = []
    for carea_element in carea_elements:
        carea_bbox = get_element_bbox(carea_element)
        cluster_elements = []
        for row_idx in range(len(td_boxes)):
            for col_idx in range(len(td_boxes[row_idx])):
                td_box_x1, td_box_y1, td_box_x2, td_box_y2 = td_boxes[row_idx][col_idx]
                td_box_with_offset = (td_box_x1 - coordinate_offset[0], td_box_y1 - coordinate_offset[1],
                                      td_box_x2 - coordinate_offset[0], td_box_y2 - coordinate_offset[1])
                if np.abs(calculate_vertical_overlap(carea_bbox, td_box_with_offset)) > 5:  # A minimum opverlap before merging the boxes
                    if calculate_overlap_percentage(carea_bbox, td_box_with_offset) > 30:  # TODO Parameterwahl begründen (10 war ganz gut?)
                        # Percentage
                        cluster_elements.append((row_idx, col_idx))
                    if np.abs(calculate_horizontal_overlap(carea_bbox, td_box_with_offset)) > 30:
                        # Pixels
                        cluster_elements.append((row_idx, col_idx))
        if len(cluster_elements) > 1:
            merge_clusters.append(cluster_elements)
    for merge_cluster in merge_clusters:
        x_min = min([td_boxes[row_idx][col_idx][0] for row_idx, col_idx in merge_cluster])
        y_min = min([td_boxes[row_idx][col_idx][1] for row_idx, col_idx in merge_cluster])
        x_max = max([td_boxes[row_idx][col_idx][2] for row_idx, col_idx in merge_cluster])
        y_max = max([td_boxes[row_idx][col_idx][3] for row_idx, col_idx in merge_cluster])
        for i, j in merge_cluster:
            td_boxes[i][j] = [x_min, y_min, x_max, y_max]


def remove_false_words(hocr_table_carea_element: etree.ElementTree):
    """
    Removes any ocrx_word span-element in the hOCR tree that contains only the result of OCR on a table element.
    False words are considered to be:
    - Higher or smaller than the word mean than 3 standard deviations
    - There are no standard characters but only puctuation
    :param hocr_table_carea_element:
    :return:
    """
    words = hocr_table_carea_element.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)
    # Remove all words that consist only of punctuation and are larger than most of the rest of the text
    word_heights = [(y2 - y1) for _, y1, _, y2 in (get_element_bbox(word) for word in words)]
    word_height_mean = np.mean(word_heights)
    word_height_std = np.std(word_heights)
    for word in words:
        parent = word.getparent()
        if word.text is not None and all([char in string.punctuation for char in word.text]):
            if parent is not None:
                parent.remove(word)
                continue
        _, y1, _, y2 = get_element_bbox(word)
        word_height = y2 - y1
        if not word_height_mean - 3 * word_height_std <= word_height <= word_height_mean + 3 * word_height_std:
            if parent is not None:
                parent.remove(word)
    for carea in hocr_table_carea_element.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES):
        carea_words = carea.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)
        if not carea_words:
            parent = carea.getparent()
            parent.remove(carea)

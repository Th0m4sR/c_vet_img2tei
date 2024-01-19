from lxml import etree
from pipeline.constants import NAMESPACES
from pipeline.hocr_tools.hocr_helpers import get_element_bbox
import numpy as np


def carea_contains_only_header(carea_element: etree.ElementTree):
    """
    Checks if all lines in the carea_element has only ocr_header elements as lines
    :param carea_element:
    :return: True if all lines are an ocr_header, False otherwise
    """
    for line_elem in carea_element.xpath(
            ".//x:span[@class='ocr_line' or @class='ocr_textfloat' or @class='ocr_header']", namespaces=NAMESPACES):
        if line_elem.attrib['class'] != "ocr_header":
            return False
    return True


def carea_contins_only_empty_words(carea_element: etree.ElementTree):
    return all([w.text is None or w.text.strip() == '' for w in carea_element.xpath(".//x:span[@class='ocrx_word']",
                                                                                    namespaces=NAMESPACES)])


def ocr_element_is_centered(carea_element: etree.ElementTree, page_element: etree.ElementTree,
                            relative_center_offset=0.3):
    """
    Checks if an ocr_carea element is centered
    :param carea_element: carea to check centering for
    :param page_element: ocr_page the ocr_carea lies on to get the line width
    :param relative_center_offset: The percentage the ocr_carea amy be off center
    :return: True if the element is centered, False otherwise
    """
    carea_x1, carea_y1, carea_x2, carea_y2 = get_element_bbox(carea_element)
    page_x1, page_y1, page_x2, page_y2 = list(
        map(int, page_element.attrib.get("title").split(";")[1].strip().split(" ")[1:]))
    page_width = page_x2 - page_x1
    page_center = page_width / 2
    carea_center = carea_x1 + ((carea_x2 - carea_x1) / 2)
    if (1 - relative_center_offset) * page_center < carea_center < (1 + relative_center_offset) * page_center:
        return True
    return False


def average_line_height_and_std(hocr_tree: etree.ElementTree):
    """
    Computes the average line height on all ocr_careas and returns mean and standard deviation of the line heights
    :param hocr_tree: hOCR tree to compute the average line height and standard deviation of
    :return: average line height and standard deviation
    """
    # print(etree.tostring(hocr_tree, pretty_print=True, encoding='unicode'))
    ocr_careas = hocr_tree.xpath("//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    line_heights = []
    for ocr_carea in ocr_careas:
        # print(ocr_carea)
        lines = ocr_carea.xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat' or @class='ocr_header']", namespaces=NAMESPACES)  # TODO careas werden nicht gefunden?
        for i in range(len(lines)):
            _, y1, _, y2 = get_element_bbox(lines[i])
            line_heights.append(y2 - y1)
    # print(line_heights)
    q1 = np.percentile(line_heights, 25)
    q3 = np.percentile(line_heights, 75)
    # Calculate the IQR
    iqr = q3 - q1
    # Define the lower and upper bounds to identify outliers
    lower_bound = q1 - 1.5 * iqr  # 1.5 is often used
    upper_bound = q3 + 1.5 * iqr  # 2 instead of 1.5 to allow more points as actual data
    # Filter out outliers within the current cluster
    line_heights = np.array(line_heights)
    line_heights = line_heights[(line_heights >= lower_bound) & (line_heights <= upper_bound)]
    return np.mean(line_heights), np.std(line_heights)


def carea_has_average_line_height(ocr_carea: etree.ElementTree, avg_line_height, line_height_std):
    """
    Checks if an ocr_carea has average line height for all lines in the ocr_carea.
    :param ocr_carea: The area to check average line height for
    :param avg_line_height: average line height
    :param line_height_std: standard deviation for the line height
    :return: True if all lines lie within 2 * std of the mean, False otherwise
    """
    lines = ocr_carea.xpath(".//x:span[@class='ocr_line' or @class='ocr_textfloat' or @class='ocr_header']",
                            namespaces=NAMESPACES)
    carea_line_heights = []
    for line in lines:
        line_x1, line_y1, line_x2, line_y2 = get_element_bbox(line)
        carea_line_heights.append(line_y2 - line_y1)
    avg_carea_line_height = np.mean(carea_line_heights)
    # print(carea_line_heights)
    # print(avg_line_height - 3 * line_height_std)
    # print(avg_carea_line_height)
    # print(avg_line_height + 3 * line_height_std)
    if avg_line_height - 15 * line_height_std < avg_carea_line_height < avg_line_height + 15 * line_height_std:  # TODO: 4 ist wirklich sehr vage, aber nötig für brd_holzbearbeitungsmechaniker_1980 zum Beispiel...
        return True
    return False


# TODO Nicht gut genug
def document_average_character_area_and_std(hocr_tree: etree.ElementTree):
    """
    Computes the average line height on all ocr_careas and returns mean and standard deviation of the line heights
    :param hocr_tree: hOCR tree to compute the average line height and standard deviation of
    :return: average line height and standard deviation
    """
    # print(etree.tostring(hocr_tree, pretty_print=True, encoding='unicode'))
    ocr_careas = hocr_tree.xpath("///x:body/x:div[@class='ocr_page']//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
    average_character_areas = []
    for ocr_carea in ocr_careas:
        words = ocr_carea.xpath(".//x:span[@class='ocrx_word']", namespaces=NAMESPACES)
        for i in range(len(words)):
            x1, y1, x2, y2 = get_element_bbox(words[i])
            average_character_areas.append((x2 - x1) / (len(words[i].text)))
    q1 = np.percentile(average_character_areas, 25)
    q3 = np.percentile(average_character_areas, 75)
    # Calculate the IQR
    iqr = q3 - q1
    # Define the lower and upper bounds to identify outliers
    lower_bound = q1 - 1.5 * iqr  # 1.5 is often used
    upper_bound = q3 + 1.5 * iqr  # 2 instead of 1.5 to allow more points as actual data
    # Filter out outliers within the current cluster
    character_areas = np.array(average_character_areas)
    character_areas = character_areas[(character_areas >= lower_bound) & (character_areas <= upper_bound)]

    # import matplotlib.pyplot as plt
    # plt.scatter(x=[i for i in range(len(character_areas))], y=character_areas, c='blue')
    # plt.axhline(y=np.mean(character_areas), c='red')
    # plt.axhline(y=np.mean(character_areas) + 1.8 * np.std(character_areas), c='blue', linestyle='--')
    # plt.axhline(y=np.mean(character_areas) - 1.8 * np.std(character_areas), c='blue', linestyle='--')
    # plt.show()

    return np.mean(character_areas), np.std(character_areas)  # stats.mode(character_areas)[0], 0


def carea_average_character_area_and_std(carea_element: etree.ElementTree):
    """
    Computes the average character area and standard deviation of the input carea
    :param carea_element:
    :return:
    """
    words = carea_element.xpath(".//x:span[@class='ocrx_word']",
                                namespaces=NAMESPACES)
    character_areas = []
    for word in words:
        x1, y1, x2, y2 = get_element_bbox(word)
        character_areas.append((x2 - x1) / (len(word.text)))
    q1 = np.percentile(character_areas, 25)
    q3 = np.percentile(character_areas, 75)
    # Calculate the IQR
    iqr = q3 - q1
    # Define the lower and upper bounds to identify outliers
    lower_bound = q1 - 1.5 * iqr  # 1.5 is often used
    upper_bound = q3 + 1.5 * iqr  # 2 instead of 1.5 to allow more points as actual data
    # Filter out outliers within the current cluster
    character_areas = np.array(character_areas)
    character_areas = character_areas[(character_areas >= lower_bound) & (character_areas <= upper_bound)]
    return np.mean(character_areas), np.std(character_areas)  # stats.mode(character_areas)[0], 0


def carea_has_average_character_areas(carea_element: etree.ElementTree,
                                      hocr_tree: etree.ElementTree,
                                      std_threshold=0.6):  # 1.8 für neue, 1 für alte
    """
    Computes the average character area of a carea and compares it to the average character area of the document.
    :param carea_element:
    :param hocr_tree:
    :param std_threshold:
    :return: True if the carea's average character area lies within std_threshold times the standard deviation of the
    document's average carea
    """
    carea_average_character_area, carea_std_character_area = carea_average_character_area_and_std(carea_element)
    document_average_character_area, document_std_character_area = document_average_character_area_and_std(hocr_tree)
    if carea_average_character_area <= document_average_character_area + std_threshold * document_std_character_area:
        return True
    return False


def ocr_word_is_empty(word_element: etree.Element) -> bool:
    """
    Checks if the text of an etree.Element is empty
    :param word_element:
    :return: True if word is empty, False otherwise
    """
    return word_element.text is None or len(word_element.text.strip()) == 0

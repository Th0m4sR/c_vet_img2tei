from lxml import etree
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image
from ..constants import NAMESPACES
from pipeline.hocr_tools.hocr_helpers import get_element_bbox


def plot_hocr_bboxes(hocr_tree: etree.ElementTree, hocr_input_image: Image, page_idx=0,
                     ocr_carea: bool = False,
                     ocr_par: bool = False,
                     ocr_header: bool = False,
                     ocr_textfloat: bool = False,
                     ocr_line: bool = False,
                     ocr_word: bool = False,
                     ocr_separator: bool = False,
                     show_plot: bool = True,
                     plot_path: str = None,
                     dpi: int = 300):
    """
    Takes an hOCR ElementTree and the image on which it was built on and plots the bboxes of each element into the image
    :param hocr_tree: hOCR ElementTree
    :param hocr_input_image: Image on which the hOCR tree is built on
    :param page_idx: index of the page in the hocr_tree
    :param ocr_carea: If True, ocr_carea bboxes are plotted, otherwise not
    :param ocr_par: If True, ocr_par bboxes are plotted, otherwise not
    :param ocr_header: If True, ocr_header bboxes are plotted, otherwise not
    :param ocr_textfloat: If True, ocr_textfloat bboxes are plotted, otherwise not
    :param ocr_line: If True, ocr_line bboxes are plotted, otherwise not
    :param ocr_word: If True, ocr_xword bboxes are plotted, otherwise not
    :param ocr_separator: If True, ocr_separator bboxes are plotted, otherwise not
    :param show_plot: If True, the plot is shown during runtime
    :param plot_path: If not None, the plot is saved in the plot_path
    :param dpi: input image DPI
    :return:
    """
    text_pages = hocr_tree.xpath("///x:body/x:div[@class='ocr_page']", namespaces=NAMESPACES)[page_idx:page_idx+1]  # TODO Unsauber, besser lösen wenn Zeit
    carea_boxes = []
    par_boxes = []
    header_boxes = []
    textfloat_boxes = []
    line_boxes = []
    word_boxes = []
    ocr_separator_boxes = []

    fig, ax = plt.subplots()

    fig.set_size_inches(hocr_input_image.width / dpi, hocr_input_image.height / dpi)
    plt.axis('off')
    for text_page in text_pages:
        text_careas = text_page.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)
        ocr_separators = text_page.xpath(".//x:div[@class='ocr_separator']", namespaces=NAMESPACES)
        for separator in ocr_separators:
            ocr_separator_boxes.append(get_element_bbox(separator))
        for text_carea in text_careas:
            # Store the coordinates
            y_lower = int(text_carea.attrib['title'].split(";")[0].split(" ")[2])
            y_upper = int(text_carea.attrib['title'].split(";")[0].split(" ")[4])
            x_lower = int(text_carea.attrib['title'].split(";")[0].split(" ")[1])
            x_upper = int(text_carea.attrib['title'].split(";")[0].split(" ")[3])
            carea_boxes.append((x_lower, y_lower, x_upper, y_upper))
            # Find the next element level
            ocr_pars = text_carea.xpath(".//x:p[@class='ocr_par']", namespaces=NAMESPACES)
            for ocr_par_elem in ocr_pars:
                text_lines = ocr_par_elem.xpath(".//x:span[@class='ocr_line']",
                                                namespaces=NAMESPACES)
                text_floats = ocr_par_elem.xpath(".//x:span[@class='ocr_textfloat']",
                                                 namespaces=NAMESPACES)
                headers = ocr_par_elem.xpath(".//x:span[@class='ocr_header']",
                                             namespaces=NAMESPACES)
                y_lower = int(text_carea.attrib['title'].split(";")[0].split(" ")[2])
                y_upper = int(text_carea.attrib['title'].split(";")[0].split(" ")[4])
                x_lower = int(text_carea.attrib['title'].split(";")[0].split(" ")[1])
                x_upper = int(text_carea.attrib['title'].split(";")[0].split(" ")[3])
                par_boxes.append((x_lower, y_lower, x_upper, y_upper))

                for header in headers:
                    y_lower = int(header.attrib['title'].split(";")[0].split(" ")[2])
                    y_upper = int(header.attrib['title'].split(";")[0].split(" ")[4])
                    x_lower = int(header.attrib['title'].split(";")[0].split(" ")[1])
                    x_upper = int(header.attrib['title'].split(";")[0].split(" ")[3])
                    header_boxes.append((x_lower, y_lower, x_upper, y_upper))

                for text_line in text_lines:
                    y_lower = int(text_line.attrib['title'].split(";")[0].split(" ")[2])
                    y_upper = int(text_line.attrib['title'].split(";")[0].split(" ")[4])
                    x_lower = int(text_line.attrib['title'].split(";")[0].split(" ")[1])
                    x_upper = int(text_line.attrib['title'].split(";")[0].split(" ")[3])
                    line_boxes.append((x_lower, y_lower, x_upper, y_upper))

                    ocrx_words = text_line.xpath(".//x:span[@class='ocrx_word']",
                                                 namespaces=NAMESPACES)
                    for word in ocrx_words:
                        y_lower = int(word.attrib['title'].split(";")[0].split(" ")[2])
                        y_upper = int(word.attrib['title'].split(";")[0].split(" ")[4])
                        x_lower = int(word.attrib['title'].split(";")[0].split(" ")[1])
                        x_upper = int(word.attrib['title'].split(";")[0].split(" ")[3])
                        word_boxes.append((x_lower, y_lower, x_upper, y_upper))

                for text_float in text_floats:
                    y_lower = int(text_float.attrib['title'].split(";")[0].split(" ")[2])
                    y_upper = int(text_float.attrib['title'].split(";")[0].split(" ")[4])
                    x_lower = int(text_float.attrib['title'].split(";")[0].split(" ")[1])
                    x_upper = int(text_float.attrib['title'].split(";")[0].split(" ")[3])
                    textfloat_boxes.append((x_lower, y_lower, x_upper, y_upper))

                    ocrx_words = text_float.xpath(".//x:span[@class='ocrx_word']",
                                                  namespaces=NAMESPACES)
                    for word in ocrx_words:
                        y_lower = int(word.attrib['title'].split(";")[0].split(" ")[2])
                        y_upper = int(word.attrib['title'].split(";")[0].split(" ")[4])
                        x_lower = int(word.attrib['title'].split(";")[0].split(" ")[1])
                        x_upper = int(word.attrib['title'].split(";")[0].split(" ")[3])
                        word_boxes.append((x_lower, y_lower, x_upper, y_upper))
    ax.imshow(hocr_input_image)
    if ocr_carea:
        for (x_lower, y_lower, x_upper, y_upper) in carea_boxes:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='red', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
    if ocr_par:
        for (x_lower, y_lower, x_upper, y_upper) in par_boxes:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='blue', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
    if ocr_header:
        for (x_lower, y_lower, x_upper, y_upper) in header_boxes:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='magenta', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
    if ocr_textfloat:
        for (x_lower, y_lower, x_upper, y_upper) in textfloat_boxes:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='yellow', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
    if ocr_line:
        for (x_lower, y_lower, x_upper, y_upper) in line_boxes:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='aqua', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
    if ocr_word:
        for (x_lower, y_lower, x_upper, y_upper) in word_boxes:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='red', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
    if ocr_separator:
        for (x_lower, y_lower, x_upper, y_upper) in ocr_separator_boxes:
            rectangle = patches.Polygon(
                [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
                closed=True, edgecolor='red', linewidth=1, fill=False)
            fig.gca().add_patch(rectangle)
    if plot_path is not None:
        fig.savefig(plot_path, dpi=dpi, bbox_inches='tight', pad_inches=0, transparent=True)
    if show_plot:
        plt.show()
    else:
        ax.cla()
        plt.close(fig)


def plot_word_confidence(hocr_tree: etree.ElementTree, hocr_input_image):
    """
    Plots the bboxes of words in the hocr_tree of a single page into the input image and adjusts the color of the box
    to the confidence value of the corresponding word.
    Green means confident, Red means not confident
    :param hocr_tree: The hOCR ElementTree of the page that will be plotted
    :param hocr_input_image: The image the hOCR was generated on
    :return:
    """
    word_elements = hocr_tree.xpath("///x:body/x:div[@class='ocr_page']//x:div[@class='ocr_carea']//x:span[@class='ocr_line' or @class='ocr_textfloat']//x:span[@class='ocrx_word']", namespaces=NAMESPACES)
    coordinates_and_confidences = []  # This stores tuples where the first 4 elements are the corners of the bboxes and the fifth is the confidence value
    for word in word_elements:
        y_lower = int(word.attrib['title'].split(";")[0].split(" ")[2])
        y_upper = int(word.attrib['title'].split(";")[0].split(" ")[4])
        x_lower = int(word.attrib['title'].split(";")[0].split(" ")[1])
        x_upper = int(word.attrib['title'].split(";")[0].split(" ")[3])
        confidence = int(word.attrib['title'].split(";")[1].lstrip().split(" ")[1])
        coordinates_and_confidences.append((x_lower, y_lower, x_upper, y_upper, confidence))
    # Preparing more things to plot the word confidences
    colors = [(1, 0, 0), (0, 1, 0)]  # Green to Red
    n_bins = 100  # Number of discrete intervals in the colormap
    cmap_name = "green_to_red_range"
    cm = LinearSegmentedColormap.from_list(cmap_name, colors, N=n_bins)
    # Doing the actual plotting
    plt.imshow(hocr_input_image)
    for (x_lower, y_lower, x_upper, y_upper, confidence) in coordinates_and_confidences:
        color = cm(confidence)
        rectangle = patches.Polygon(
            [(x_lower, y_lower), (x_lower, y_upper), (x_upper, y_upper), (x_upper, y_lower)],
            closed=True, edgecolor=color, linewidth=1, fill=False)
        plt.gca().add_patch(rectangle)
    plt.show()

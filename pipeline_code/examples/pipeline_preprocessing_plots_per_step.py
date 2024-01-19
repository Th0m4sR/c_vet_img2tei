from lxml import etree
import os
from PIL import Image
from pipeline.resegmentation.paragraph_splitting_y import split_ocr_careas_horizontally
from pipeline.resegmentation.paragraph_merging_x import merge_careas_on_x_axis_in_document_tree
from pipeline.hocr_tools.hocr_helpers import combine_hocr_pages
from pipeline.tei_encoding.layout_extraction import get_header_elements, remove_pre_text_elements, \
    remove_empty_careas, get_body_and_appendix_tree
from pipeline.hocr_tools.hocr_element_visualization import plot_hocr_bboxes
from pytesseract import pytesseract
from pipeline.pipeline_logger import file_logger
from pipeline.constants import NAMESPACES


hocr_directory = 'data_directory/OffenegesetzeDE/tesseract_output/brd_kartographen_1975'
img_directory = 'data_directory/OffenegesetzeDE/scantailor_output/brd_kartographen_1975'

hocr_trees = [etree.parse(os.path.join(hocr_directory, hocr_filename)) for hocr_filename in os.listdir(hocr_directory)
              if hocr_filename.endswith(".hocr")]
images = [Image.open(os.path.join(img_directory, img_filename)) for img_filename in os.listdir(img_directory)
          if img_filename.endswith(".tif")]
hocr_tree = combine_hocr_pages(hocr_trees)
logger = file_logger()
max_area_dist = 50


def plot_all_pages(hocr_tree, images, plot_path_basename):
    pages = hocr_tree.xpath(".//x:div[@class='ocr_page']", namespaces=NAMESPACES)
    for i in range(len(pages)):
        plot_hocr_bboxes(hocr_tree, images[i], page_idx=i,
                         ocr_carea=True,
                         ocr_word=False,
                         show_plot=False,
                         plot_path=plot_path_basename + "_" + str(i) + ".png")


plot_all_pages(hocr_tree, images, 'z_pipeline_plots/0_basic_ocr')
# Step 1: Split the ocr_carea elements
try:
    split_ocr_careas_horizontally(hocr_tree)
    logger.info("Split careas horizontally")
    plot_all_pages(hocr_tree, images, 'z_pipeline_plots/1_carea_splits')
except Exception as e:
    logger.exception("Error splitting careas horizontally: %s", e, exc_info=True)

# Step 2: Extract the page headers
try:
    headers = [get_header_elements(page) for page in hocr_tree.xpath("//x:div[@class='ocr_page']",
                                                                     namespaces=NAMESPACES)]
    plot_all_pages(hocr_tree, images, 'z_pipeline_plots/2_removed_headers')
    logger.info("Extracted headers")
except Exception as e:
    headers = [[] for _ in range(len(hocr_tree.xpath("//x:div[@class='ocr_page']",
                                                     namespaces=NAMESPACES)))]
    logger.exception("Error extracting header elements: %s", e, exc_info=True)

# Step 3: Remove any elements that do not belong to the regulation
try:
    remove_pre_text_elements(hocr_tree, logger=logger)
    logger.info("Removed pre-text elements")
    plot_all_pages(hocr_tree, images, 'z_pipeline_plots/3_per_text_removal')
except Exception as e:
    logger.exception("Error removing pre-text elements: %s", e, exc_info=True)

# Step 4: Split body and appendix
try:
    body_tree, appendix_tree = get_body_and_appendix_tree(hocr_tree)
    appendix_page_start_idx = len(body_tree.xpath("//x:div[@class='ocr_page']", namespaces=NAMESPACES))
    logger.info("Split body from appendix")
    plot_all_pages(body_tree, images[:appendix_page_start_idx], 'z_pipeline_plots/4_basic_body')
    plot_all_pages(appendix_tree, images[appendix_page_start_idx:], 'z_pipeline_plots/4_basic_appendix')
except Exception as e:
    logger.exception("Unable to split body from appendix: %s", e, exc_info=True)
    raise ValueError("The document does not have the required form to be encoded")
# Storing at which page index the appendix starts
text_headers = headers[:appendix_page_start_idx]
appendix_headers = headers[appendix_page_start_idx:]
logger.info("Separated headers")

# Step 5: Prepare the body for encoding
# 5.1: Remove the lines that are in the image (regulations from the 70s have a line between text columns)
try:
    pre_empty_area_removal_carea_count = len(body_tree.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)) + len(body_tree.xpath(".//x:div[@class='ocr_separator']", namespaces=NAMESPACES))
    remove_empty_careas(body_tree, images)
    post_empty_area_removal_carea_count = len(body_tree.xpath(".//x:div[@class='ocr_carea']", namespaces=NAMESPACES)) + len(body_tree.xpath(".//x:div[@class='ocr_separator']", namespaces=NAMESPACES))
    logger.info("Removed lines from image and hOCR")
    # Documents where a line was between the text columns often have worse results.
    # Therefore, some of the steps have to be applied again
    if post_empty_area_removal_carea_count < pre_empty_area_removal_carea_count:
        logger.info("Pre-text elements had to be removed")
        body_tree = combine_hocr_pages([etree.fromstring(
            bytes(pytesseract.run_and_get_output(image, 'hocr', 'deu', '--dpi 300', '--psm 3'), 'utf-8')) for image in
            images[:appendix_page_start_idx]])
        text_headers = [get_header_elements(page) for page in
                        body_tree.xpath("//x:div[@class='ocr_page']", namespaces=NAMESPACES)]
        split_ocr_careas_horizontally(body_tree)
        remove_pre_text_elements(body_tree, logger=logger)
        remove_empty_careas(body_tree, images)
    plot_all_pages(body_tree, images, 'z_pipeline_plots/5_removed_lines')
except Exception as e:
    logger.exception("Error removing lines from the body tree: %s", e, exc_info=True)

# 5.2: Re-merge the elements on the x-axis that were detected separately
# Erweitern statt mergen in body (Dafür nur 2er-cluster machen)
#  Dafür: minimales x1, maximales y1, maximales x2, minimales y2 aus den beiden clustern
try:
    merge_careas_on_x_axis_in_document_tree(body_tree, max_area_dist=max_area_dist)
    plot_all_pages(body_tree, images[:appendix_page_start_idx], 'z_pipeline_plots/6_merged_lines_body')
    logger.info("Merged careas in body-tree")
except Exception as e:
    logger.exception("Error merging careas in body tree: %s", e, exc_info=True)
try:
    # merge_careas_on_x_axis_in_document_tree(appendix_tree, max_area_dist=max_area_dist)
    plot_all_pages(appendix_tree, images[appendix_page_start_idx:], 'z_pipeline_plots/6_merged_lines_appendix')
    # logger.info("Merged careas in appendix-tree")
except Exception as e:
    logger.exception("Error merging careas in appendix tree: %s", e, exc_info=True)

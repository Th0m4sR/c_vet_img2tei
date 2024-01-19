from lxml import etree
from PIL import Image
import os
from pipeline.hocr_tools.hocr_helpers import combine_hocr_pages
from pipeline.text_encoding import encode_hocr_tree_in_tei
from pipeline.pipeline_logger import file_logger
import time


NAMESPACES = {'x': 'http://www.w3.org/1999/xhtml'}

# VET
hocr_directory = 'data_directory/OffenegesetzeDE/tesseract_output/brd_fachkraft_küche_2022'
img_directory = 'data_directory/OffenegesetzeDE/scantailor_output/brd_fachkraft_küche_2022'


hocr_trees = [etree.parse(os.path.join(hocr_directory, hocr_filename)) for hocr_filename in os.listdir(hocr_directory)
              if hocr_filename.endswith(".hocr")]
imgs = [Image.open(os.path.join(img_directory, img_filename)) for img_filename in os.listdir(img_directory)
        if img_filename.endswith(".tif")]
tree = combine_hocr_pages(hocr_trees)


start_time = time.time()
logger = file_logger()
tei_tree = encode_hocr_tree_in_tei(hocr_tree=tree, images=imgs, logger=logger)
print("--- %s seconds ---" % (time.time() - start_time))
tei_tree.write('brd_fachkraft_küche_2022.xml', pretty_print=True, encoding='utf-8')

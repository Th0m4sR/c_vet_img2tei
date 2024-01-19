from lxml import etree
from PIL import Image
import os
from pipeline.hocr_tools.hocr_helpers import combine_hocr_pages
from pipeline.text_encoding import encode_hocr_tree_in_tei
import time
from concurrent.futures import ProcessPoolExecutor
from pipeline.pipeline_logger import file_logger


vet_files = [name.split(".")[0] for name in os.listdir('data_directory/OffenegesetzeDE/scantailor_output/')]
vet_tesseract_directory = 'data_directory/OffenegesetzeDE/tesseract_output/'
vet_scantailor_directory = 'data_directory/OffenegesetzeDE/scantailor_output/'
vet_tei_output_directory = 'data_directory/tei_output/vet/'
vet_logs_directory = 'data_directory/logs/vet/'


# Here, the regulations are in directories for each year and need to be joined by an additional layer
cvet_base_dir = 'data_directory/fortbildungsordnungen/scantailor_output/'
cvet_files = []
cvet_years = [year_dir for year_dir in os.listdir(cvet_base_dir)]
for year in cvet_years:
    year_dir = os.path.join(cvet_base_dir, year)
    for img_file in os.listdir(year_dir):
        cvet_files.append(os.path.join(year, img_file.split(".")[0]))

cvet_tesseract_directory = 'data_directory/fortbildungsordnungen/tesseract_output/'
cvet_scantailor_directory = 'data_directory/fortbildungsordnungen/scantailor_output/'
cvet_tei_output_directory = 'data_directory/tei_output/cvet/'
cvet_logs_directory = 'data_directory/logs/cvet/'


def manage_encodings(max_workers, input_files,
                     tesseract_directory,
                     scantailor_directory,
                     tei_output_directory,
                     logs_directory):
    hocr_dirs = [os.path.join(tesseract_directory, regulation_subdirectory) for regulation_subdirectory in input_files]
    img_dirs = [os.path.join(scantailor_directory, regulation_subdirectory) for regulation_subdirectory in input_files]
    out_files = [os.path.join(tei_output_directory, os.path.basename(regulation_subdirectory) + ".xml") for regulation_subdirectory in input_files]
    log_files = [os.path.join(logs_directory, os.path.basename(regulation_subdirectory) + ".log") for regulation_subdirectory in input_files]
    encoding_parameters = list(zip(hocr_dirs, img_dirs, out_files, log_files))
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        executor.map(initialize_encoding, encoding_parameters)


def initialize_encoding(encoding_parameters):
    hocr_directory, img_directory, out_file, log_file = encoding_parameters
    if os.path.exists(out_file):
        print(f"File '{out_file}' already exists")
        return
    hocr_trees = [etree.parse(os.path.join(hocr_directory, hocr_filename)) for hocr_filename in os.listdir(hocr_directory)
                  if hocr_filename.endswith(".hocr")]
    imgs = [Image.open(os.path.join(img_directory, img_filename)) for img_filename in os.listdir(img_directory)
            if img_filename.endswith(".tif")]
    logger = file_logger(log_file)
    tree = combine_hocr_pages(hocr_trees)
    start_time = time.time()
    tei_tree = encode_hocr_tree_in_tei(hocr_tree=tree, images=imgs, logger=logger)
    logger.info("--- Finished process after %s seconds ---" % (time.time() - start_time))
    tei_tree.write(out_file, pretty_print=True, encoding='utf-8')
    print(f"Wrote to {out_file}")


if __name__ == '__main__':
    manage_encodings(max_workers=8, input_files=vet_files,
                     tesseract_directory=vet_tesseract_directory,
                     scantailor_directory=vet_scantailor_directory,
                     tei_output_directory=vet_tei_output_directory,
                     logs_directory=vet_logs_directory)
    manage_encodings(max_workers=8, input_files=cvet_files,
                     tesseract_directory=cvet_tesseract_directory,
                     scantailor_directory=cvet_scantailor_directory,
                     tei_output_directory=cvet_tei_output_directory,
                     logs_directory=cvet_logs_directory)

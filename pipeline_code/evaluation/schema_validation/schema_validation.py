from lxml import etree
from PIL import Image
import os
import xmlschema
# Wichtige Imports:
from pipeline.hocr_tools.hocr_helpers import combine_hocr_pages
from pipeline.text_encoding import encode_hocr_tree_in_tei
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pipeline.pipeline_logger import file_logger
from typing import Tuple
from pipeline.constants import NAMESPACES, LOG_DIRECTORY
# Helper Imports

SUCCESS_MSG = "Validation successful"

vet_tei_output_directory = 'data_directory/tei_output/vet/'
vet_schema_log_dir = r"data_directory\evaluation\schema_validation_logs\vet"
vet_tei_files = [os.path.join(vet_tei_output_directory, file_name) for file_name in os.listdir(vet_tei_output_directory)]

cvet_tei_output_directory = 'data_directory/tei_output/cvet/'
cvet_schema_log_dir = r"data_directory\evaluation\schema_validation_logs\cvet"
cvet_tei_files = [os.path.join(cvet_tei_output_directory, file_name) for file_name in os.listdir(cvet_tei_output_directory)]

schema_location = "https://tei-c.org/release/xml/tei/custom/schema/xsd/tei_all.xsd"
xml_schema = xmlschema.XMLSchema(schema_location)


def validate_xml(xml_file, xsd_schema, log_path):
    logger = file_logger(log_file_path=log_path)
    try:
        xsd_schema.validate(xml_file)
        logger.info("Validation successful")
        return True
    except xmlschema.validators.exceptions.XMLSchemaChildrenValidationError as e:
        logger.exception("Error validating the XML document: %s", e, exc_info=True)
        return False


def manage_validations(max_workers, tei_files, logs_directory):
    schema_location_params = [xml_schema for _ in range(len(tei_files))]
    log_files = [os.path.join(logs_directory, os.path.basename(regulation_subdirectory).split(".")[0] + ".log") for regulation_subdirectory in tei_files]
    encoding_parameters = list(zip(tei_files, schema_location_params, log_files))
    # for x, y, z in encoding_parameters:
    #     print(f"{x}\t\t------------->\t\t{y}\t\t------------->\t\t{z}")
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        executor.map(initialize_validation, encoding_parameters)
    return log_files


def initialize_validation(validation_params: Tuple[str, xmlschema.XMLSchema, str]):
    xml_file, xsd_file, log_path = validation_params
    validate_xml(xml_file, xsd_file, log_path)


if __name__ == '__main__':
    vet_result_logs = manage_validations(max_workers=10, tei_files=vet_tei_files, logs_directory=vet_schema_log_dir)
    cvet_result_logs = manage_validations(max_workers=10, tei_files=cvet_tei_files, logs_directory=cvet_schema_log_dir)

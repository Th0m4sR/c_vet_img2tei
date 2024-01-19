import os
import subprocess
import asyncio
import aiofiles
import tempfile
import shutil
from PIL import Image
from lxml import etree
from pipeline.hocr_tools.hocr_helpers import combine_hocr_pages
from pipeline.text_encoding import encode_hocr_tree_in_tei
import traceback
from fastapi import UploadFile
from webapp_backend.business_logic.xml_response_parser import query_and_parse_regulations
from pathlib import Path
from typing import List
from webapp_backend.data_access.exist_connector import store_regulation


TMP_ORIGINAL_FILES = 'original'
TMP_IMAGES = 'images'
TMP_PREPROCESSED_IMAGES = 'scantailor'
TMP_TESSERACT_OUT = 'tesseract'
IMAGE_KEEPING_DIR = '/upload/image/path/uploads'  # This needs to be the path where the uploads are stored

# test_file = '/path/to/test/file.pdf'


# TODO: Call this function separately to have the vet_files on server side. Then easy peasy lemon squeezy
async def initialize_workspace(upload_files: List[UploadFile],
                               progress_dict=None,
                               task_id: int = 0):
    temp_dir = None
    if progress_dict is None:
        progress_dict = {}
    try:
        progress_dict[task_id] = (0, "Dateien werden hochgeladen...")
        # Creating the temporary vet_files
        temp_dir = tempfile.mkdtemp()
        # temp_dir = '/tmp/tmpmi1e3yjd'
        # Create the directories for each step in the processing
        original_file_dir = os.path.join(temp_dir, TMP_ORIGINAL_FILES)
        os.mkdir(original_file_dir)

        # Store the file in the "original" subdirectory
        # new_file_path = os.path.join(original_file_dir, os.path.basename(test_file))
        # shutil.copy(test_file, new_file_path)

        for regulation in upload_files:
            output_path = os.path.join(original_file_dir, regulation.filename)
            async with aiofiles.open(output_path, "wb") as buffer:
                while chunk := await regulation.read(1024):
                    await buffer.write(chunk)
        return temp_dir
    except Exception as e:
        print(traceback.format_exc())


async def apply_pdf_to_ppm(original_file_dir, image_file_dir):
    image_file_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']
    # Apply pdftoppm to the file in the directory
    for pdf_file in os.listdir(original_file_dir):
        if pdf_file.endswith(".pdf"):
            # Remove the .pdf extension from the file name
            file_name_without_extension = os.path.splitext(pdf_file)[0]
            # Input and output paths
            pdf_file_path = os.path.join(original_file_dir, pdf_file)
            output_path = os.path.join(image_file_dir, file_name_without_extension)
            # Execute pdftoppm
            pdf_to_ppm_command = ['pdftoppm', '-r', '300', pdf_file_path, output_path, '-png']
            # subprocess.run(pdf_to_ppm_command)
            process = await asyncio.create_subprocess_exec(*pdf_to_ppm_command,
                                                           stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)
            await process.communicate()
        elif pdf_file.split('.')[-1] in image_file_extensions:
            shutil.copy(os.path.join(original_file_dir, pdf_file),
                        os.path.join(image_file_dir, pdf_file))
        else:
            raise ValueError(f"{pdf_file} is neither PDF nor image.")


async def apply_scantailor_universal(image_file_dir, scantailor_file_dir):
    # Apply scantailor to all image vet_files in the directory
    # scantailor-universal-cli --dpi=300 --output-dpi=300 --layout=1 "$ppm_folder" "$output_dir/$output_folder"
    scantailor_command = [
        'scantailor-universal-cli',
        '--dpi=300',
        '--output-dpi=300',
        '--layout=1',
        image_file_dir,
        scantailor_file_dir
    ]
    process = await asyncio.create_subprocess_exec(*scantailor_command,
                                                   stdout=asyncio.subprocess.PIPE,
                                                   stderr=asyncio.subprocess.PIPE)
    await process.communicate()


async def apply_tesseract(scantailor_file_dir, tesseract_file_dir):
    for image_file in os.listdir(scantailor_file_dir):
        if image_file.endswith(".tif"):
            # Remove the .tif extension from the file name
            file_name_without_extension = os.path.splitext(image_file)[0]
            # Input and output paths
            scantailor_file_path = os.path.join(scantailor_file_dir, image_file)
            output_path = os.path.join(tesseract_file_dir, file_name_without_extension)
            tesseract_command = ['tesseract', scantailor_file_path, output_path, '-l', 'deu', '--dpi', '300', 'hocr']
            subprocess.run(tesseract_command)
            process = await asyncio.create_subprocess_exec(*tesseract_command,
                                                           stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)
            await process.communicate()


async def encode_upload(scantailor_file_dir, tesseract_file_dir):
    hocr_files = [file for file in os.listdir(tesseract_file_dir) if file.endswith(".hocr")]
    image_files = [file for file in os.listdir(scantailor_file_dir) if file.endswith(".tif")]
    hocr_files.sort()
    image_files.sort()
    hocr_trees = [etree.parse(os.path.join(tesseract_file_dir, hocr_filename)) for hocr_filename in hocr_files]
    imgs = [Image.open(os.path.join(scantailor_file_dir, img_filename)) for img_filename in image_files]
    tree = combine_hocr_pages(hocr_trees)
    regulation_tree = encode_hocr_tree_in_tei(hocr_tree=tree, images=imgs)
    # TODO Define title
    title = hash(regulation_tree)

    parent = Path(scantailor_file_dir).parent.absolute()
    xml_path = os.path.join(parent, f"{title}.xml")
    regulation_tree.write(xml_path)
    regulation_tree = etree.parse(xml_path)

    if store_regulation(title=title, regulation_tree=regulation_tree):
        return title
    else:
        raise ValueError(f"Failed to store regulation with title '{title}'")


async def process_upload_files(workspace_path, progress_dict=None, task_id=0):
    if progress_dict is None:
        progress_dict = {}
    try:
        # Create the directories for each step in the processing
        original_file_dir = os.path.join(workspace_path, TMP_ORIGINAL_FILES)
        # os.mkdir(original_file_dir)
        image_file_dir = os.path.join(workspace_path, TMP_IMAGES)
        os.mkdir(image_file_dir)
        scantailor_file_dir = os.path.join(workspace_path, TMP_PREPROCESSED_IMAGES)
        os.mkdir(scantailor_file_dir)
        tesseract_file_dir = os.path.join(workspace_path, TMP_TESSERACT_OUT)
        os.mkdir(tesseract_file_dir)

        progress_dict[task_id] = (20, {"message": "Bilder werden extrahiert..."})
        await apply_pdf_to_ppm(original_file_dir, image_file_dir)
        progress_dict[task_id] = (40, {"message": "Scans werden verarbeitet..."})
        await apply_scantailor_universal(image_file_dir, scantailor_file_dir)
        progress_dict[task_id] = (60, {"message": "Text wird erkannt..."})
        await apply_tesseract(scantailor_file_dir, tesseract_file_dir)
        progress_dict[task_id] = (80, {"message": "Ergebnisse werden verarbeitet..."})
        created_title = await encode_upload(scantailor_file_dir, tesseract_file_dir)
        # Finally, store the uploaded images on the server for permanent keeping
        shutil.copytree(workspace_path, os.path.join(IMAGE_KEEPING_DIR, os.path.basename(workspace_path)))
        created_regulation = query_and_parse_regulations(regulation_query_params=None,
                                                         document_title=str(created_title))[0]
        progress_dict[task_id] = (100, {"message": "Fertig!", "resource": created_regulation})
        # print(temp_dir)
        return created_title
    except Exception as e:
        progress_dict[task_id] = (0, {"message": "Ein Fehler ist aufgetreten. Upload abgebrochen."})
        print(traceback.format_exc())
    finally:
        if workspace_path is not None:
            shutil.rmtree(workspace_path)
        # TODO Das anders managen
        # del progress_dict[task_id]

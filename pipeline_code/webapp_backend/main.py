from fastapi import FastAPI, UploadFile, Form, File, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Annotated

import webapp_backend.application_logic.basemodels as models
from webapp_backend.business_logic import xml_response_parser, upload_processor, update_processor
import webapp_backend.business_logic.regulation_deletion as regulation_deletion

app = FastAPI()

# TODO Use redis instead
task_progress = {}
task_id = 0

running_tasks = {}

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> models.TransferObject:
    to = models.TransferObject()
    to.string_parameter = "Hello There!"
    return to


@app.post("/create/")
async def upload_file(regulation_files: Annotated[List[UploadFile], File()],
                      background_tasks: BackgroundTasks,
                      dokumententitel = Form(None),
                      herausgeber = Form(None),
                      verlag = Form(None),
                      erscheinungsort = Form(None),
                      erscheinungsdatum = Form(None),
                      erscheinungsjahr = Form(None),
                      erlassdatum = Form(None),
                      inkrafttreten = Form(None),
                      seitenzahl = Form(None)):
    """
    Stores the uploaded vet_files and applies the required OCR steps. Metadata can be included
    :param regulation_files: vet_files to process
    :param regulation_metadata: JSON object with the added metadata
    :param background_tasks
    :return:
    """
    # From FastAPI documentation: https://fastapi.tiangolo.com/tutorial/request-forms/
    # You can declare multiple Form parameters in a path operation, but you can't also declare Body fields that you
    # expect to receive as JSON, as the request will have the body encoded using application/x-www-form-urlencoded
    # instead of application/json.
    # This is not a limitation of FastAPI, it's part of the HTTP protocol.
    #
    # This is why regulation_metadata needs to be received as string
    global task_id
    task_id += 1
    print("ADDING BACKGROUND TASK")
    local_task_id = task_id
    workspace_path = await upload_processor.initialize_workspace(regulation_files)
    background_tasks.add_task(upload_processor.process_upload_files,
                              workspace_path,
                              progress_dict=task_progress,
                              task_id=local_task_id)
    print(dokumententitel)
    print(herausgeber)
    print(verlag)
    print(erscheinungsort)
    print(erscheinungsdatum)
    print(erscheinungsjahr)
    print(erlassdatum)
    print(inkrafttreten)
    print(seitenzahl)
    print("UPLOAD STARTED")
    return {"task_id": task_id}


@app.post("/search/")
async def search_regulations(search_parameters: models.QueryParametersRegulation):  # Dict[str, str]
    # TODO Input sanitize in der Methode
    # result = query_regulation(regulation_filter)
    params = search_parameters.dict()
    if not params:
        params = None
    result = xml_response_parser.query_and_parse_regulations(params)
    return result


@app.get("/regulations/{regulation_name}")
async def get_regulation_by_id(regulation_name: str,
                               version: str = Query(None, description="Regulation version (optional)")):
    try:
        regulation = xml_response_parser.query_and_parse_regulations(regulation_query_params=None,
                                                                     document_title=regulation_name,
                                                                     version=version)[0]
        return regulation
    except:
        import traceback
        traceback.print_exc()
        return "no regulation found"


@app.post("/update/")
async def update_regulation(updated_regulation: models.UpdatedRegulation):
    if update_processor.update_regulation(exist_name=updated_regulation.exist_name,
                                          xml_string=updated_regulation.xml_regulation):
        return {"message": "Änderungen wurden gespeichert",
                "success": True}
    return {"message": "Ein Fehler ist aufgetreten",
            "success": False}


@app.delete("/delete/{regulation_name}")
async def delete_regulation(regulation_name: str):
    if regulation_deletion.delete_regulation(regulation_name):
        return {"message": "Verordnung wurde gelöscht",
                "success": True}
    return {"message": "Ein Fehler ist aufgetreten",
            "success": False}


# Upload progress monitoring
@app.get("/task_progress/{task_id}")
async def get_task_progress(task_id: int):
    if task_id in task_progress:
        progress = task_progress[task_id]
        response = models.ProgressState(progress=progress[0],
                                        content=progress[1])
        return response
    else:
        return JSONResponse(content={"error": "Task not found."})


@app.get("/cancel_task/{task_id}")
async def cancel_task(task_id: int):
    if task_id in running_tasks:
        running_tasks[task_id].cancel()
        task_progress[task_id] = (0, {"message": "Upload abgebrochen."})
        # del running_tasks[task_id]
        return {"message": f"task {task_id} canceled"}
    else:
        return {"message": f"no task with {task_id}"}


# Viewing the uploaded vet_files
upload_path = '/upload/image/path/uploads'  # This needs to be the path where the uploads are stored
app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")

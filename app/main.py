from celery.result import AsyncResult
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from pydantic import BaseModel, Field

from uuid import uuid4

from app.tasks import celery_app, process_document

from pathlib import Path


class HealthResponse(BaseModel):
    status: str
    service: str


class UploadRequest(BaseModel):
    text: str = Field(min_length=1, description="Text to process")
    seconds: int = Field(
        default=3, ge=0, le=60, description="Simulated processing time in seconds"
    )


class TaskCreated(BaseModel):
    task_id: str
    file_id: str
    status: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: dict | None = None

class Result(BaseModel):
    message: str
    result: str
    status: str

########################################


app = FastAPI(title="Open Filint", version="1.0.0")

MAX_FILE_SIZE = 10 * 1024 * 1024

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api")


@app.post("/tasks", response_model=TaskCreated, status_code=202)
def create_task(
    file: UploadFile = File(...)
) -> TaskCreated:
    # 202 Accepted: the work is only queued here, not done yet.
    # The worker picks it up from Redis in the background.

    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="The file size is over 10 MB, this API just accept files under 10 MB")
    
    if not file.filename.lower().endswith((".pdf", ".png", ".jpg")):
        raise HTTPException(status_code=400, detail="Format not allowed")

    file_id = str(uuid4())

    extension = file.filename[-4:]

    url = f"app/bucket/{file_id}{extension}"

    with open(url, "wb") as f:
        f.write(file.file.read())

    task = process_document.delay(url=url, original_file_name=file.filename, file_id=file_id)

    return TaskCreated(task_id=task.id, file_id=file_id, status="queued")



@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str) -> TaskStatus:
    result = AsyncResult(task_id, app=celery_app)
    response = TaskStatus(task_id=task_id, status=result.status)
    if result.successful():
        response.result = result.result
    elif result.failed():
        response.result = {"error": str(result.result)}
    return response

@app.get("/results/{file_id}", response_model=Result)
def get_result(file_id: str):
    if f"output/{file_id}.md".is_file():
        with open(f"output/{file_id}.md", "r", encoding="utf-8") as file:
            text = file.read()
        return Result(message="Your text is available", result=text, status="Available" )
    else:
        return Result(message="check if you used a correct file_id, if you did, it should be processing", result="", status="Not available" )
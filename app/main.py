from celery.result import AsyncResult
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.tasks import celery_app, process_text


class HealthResponse(BaseModel):
    status: str
    service: str


class TaskRequest(BaseModel):
    text: str = Field(min_length=1, description="Text to process")
    seconds: int = Field(
        default=3, ge=0, le=60, description="Simulated processing time in seconds"
    )


class TaskCreated(BaseModel):
    task_id: str
    status: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: dict | None = None


app = FastAPI(title="Queue Demo", version="1.0.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api")


@app.post("/tasks", response_model=TaskCreated, status_code=202)
def create_task(request: TaskRequest) -> TaskCreated:
    # 202 Accepted: the work is only queued here, not done yet.
    # The worker picks it up from Redis in the background.
    task = process_text.delay(request.text, request.seconds)
    return TaskCreated(task_id=task.id, status="queued")


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str) -> TaskStatus:
    result = AsyncResult(task_id, app=celery_app)
    response = TaskStatus(task_id=task_id, status=result.status)
    if result.successful():
        response.result = result.result
    elif result.failed():
        response.result = {"error": str(result.result)}
    return response

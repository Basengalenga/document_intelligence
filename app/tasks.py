import os
import time

from celery import Celery

# Redis plays two roles here:
#   - broker: the queue where pending tasks wait for a worker
#   - result backend: where workers store each task's result
celery_app = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)


@celery_app.task
def process_text(text: str, seconds: int = 3) -> dict:
    # time.sleep simulates slow work (e.g. model inference) so that the
    # queue's async behaviour is visible while polling GET /tasks/{task_id}.
    time.sleep(seconds)
    return {
        "original": text,
        "word_count": len(text.split()),
        "upper": text.upper(),
    }

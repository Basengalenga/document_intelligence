import os
import time
from pathlib import Path

from celery import Celery

import opendataloader_pdf
from PIL import Image



# Redis plays two roles here:
#   - broker: the queue where pending tasks wait for a worker
#   - result backend: where workers store each task's result
celery_app = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "db+postgresql+psycopg2://admin:admin123@postgres:5432/celery"),
)


@celery_app.task(
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_document(url: str, original_file_name: str, file_id: str) -> dict:

    #############################################################333333

    if url[-3:] == "png" or url[-3:]== "jpg":
        img_path = url
        pdf_path = f"/tmp/{url.split('/')[-1][:-4]}.pdf"

        image = Image.open(img_path)
        image.convert("RGB").save(pdf_path)
    else:
        pdf_path=url


    opendataloader_pdf.convert(
        input_path=[pdf_path],
        output_dir="output/",
        format="markdown,json",
        hybrid="docling-fast",     
        hybrid_mode="full",        
        hybrid_url="http://hybrid-ocr:5002"
    )


    ###############################################################3

    bucket_status = Path(url).is_file()

    return {
        "recibido": url,
        "nombre_original":original_file_name,
        "file_id":file_id,
        "recordatorio": "Go to /resutls to get your txt. Use the file_id. NOT THE TASK ID"
    }

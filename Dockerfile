FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    default-jre-headless \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home appuser \
    && mkdir /app/app/bucket /app/app/output \
    && chown -R appuser:appuser /app/app/bucket /app/app/output 

USER appuser

# The api, worker and flower services all reuse this image with their own command.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app/app/bucket

USER appuser

# The api, worker and flower services all reuse this image with their own command.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Queue Demo — FastAPI + Celery + Redis

A minimal, easy-to-follow example of background task processing:
a FastAPI endpoint enqueues work into a Redis queue, and a Celery worker
picks it up and processes it in the background.

```
             POST /tasks                 queue                 consume
  client ─────────────────▶ FastAPI ──────────────▶ Redis ──────────────▶ Celery worker
                               (api)              (broker +              process_text()
                              :8001              result backend)         writes the result
                                                                         back to Redis
```

Three moving parts, each in its own container:

| Service  | What it does                                                        |
| -------- | ------------------------------------------------------------------- |
| `redis`  | Holds the queue of pending tasks **and** the results of finished ones |
| `api`    | FastAPI app: accepts requests, enqueues tasks, serves task status    |
| `worker` | Celery worker: consumes tasks from the queue and executes them       |

All three Python services share **one image** with different start commands.

## Run it

```bash
docker compose up --build
```

The demo task (`process_text`) sleeps for a configurable number of seconds
to simulate slow work, then returns the word count and uppercased text.

```bash
# 1. Enqueue a task — returns immediately with a task id
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"text": "hello queue world", "seconds": 5}'
# {"task_id":"d4c0...","status":"queued"}

# 2. Poll the task — while the worker is busy it is PENDING
curl http://localhost:8001/tasks/<task_id>
# {"task_id":"d4c0...","status":"PENDING","result":null}

# 3. After ~5s the result is ready
curl http://localhost:8001/tasks/<task_id>
# {"task_id":"d4c0...","status":"SUCCESS",
#  "result":{"original":"hello queue world","word_count":3,"upper":"HELLO QUEUE WORLD"}}
```

> `PENDING` means "not finished yet" — it covers both *waiting in the queue*
> and *currently running*. `SUCCESS` / `FAILURE` are the terminal states.

## Flower (optional monitoring UI)

Flower is a web UI that shows the workers, the task history and success/failure
rates in real time. It is deliberately **not** part of the default stack, so the
core demo stays as small as possible — start it when you want to *see* the queue:

```bash
docker compose --profile monitoring up -d
```

Then open http://localhost:5555 while enqueueing tasks: the *Tasks* tab lists
every task with its state, runtime and result; the *Workers* tab shows the
connected worker and its concurrency (2 child processes). Note that Flower
only records tasks from the moment it starts — tasks enqueued before it was
running won't appear.

## Endpoints

| Method | Path                | Description                                  |
| ------ | ------------------- | -------------------------------------------- |
| GET    | `/health`           | Liveness check                                |
| POST   | `/tasks`            | Enqueue a text for processing (returns 202)   |
| GET    | `/tasks/{task_id}`  | Status (`PENDING`/`SUCCESS`/`FAILURE`) + result |

Interactive docs: http://localhost:8001/docs

## Project layout

```
queue-demo/
├── app/
│   ├── main.py        # FastAPI: POST /tasks, GET /tasks/{id}, GET /health
│   └── tasks.py       # Celery app (broker/backend config) + process_text task
├── Dockerfile         # one image, reused by api / worker / flower
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Exercise: batch text processing with the sentiment model

This project is the starting point. The goal is to reuse the model from
`../sentiment-api` (`distilbert-base-uncased-finetuned-sst-2-english`)
so texts can be classified asynchronously in batches:

1. Move the model loading into the worker (e.g. load the HF pipeline once
   when `tasks.py` is imported, like `sentiment-api/app/main.py` does).
   Only the worker should load the model — the API stays lightweight.
2. Replace the body of `process_text` with real inference: return
   `{"label": ..., "score": ...}` instead of the word count.
3. Add a `POST /tasks/batch` endpoint that accepts a **list** of texts and
   enqueues one task per text (or one task for the whole batch — compare!).
4. Watch the concurrency in Flower: with `--concurrency=2`, how many texts
   are processed at the same time? What happens if you scale the worker with
   `docker compose up -d --scale worker=3`?

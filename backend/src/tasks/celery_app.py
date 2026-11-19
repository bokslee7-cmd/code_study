import os

from celery import Celery  # type: ignore[import-untyped]
from kombu import Queue  # type: ignore[import-untyped]

TASK_QUEUES = (
    Queue("default"),
    Queue("document_generation"),
    Queue("practice_generation"),
    Queue("cleanup"),
)
TASK_TIME_LIMIT_SECONDS = 300


def get_redis_url() -> str:
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        raise RuntimeError("REDIS_URL environment variable is required")
    return redis_url


redis_url = get_redis_url()
app = Celery(
    "code_learning",
    broker=redis_url,
    backend=redis_url,
    include=["src.tasks.document_generation"],  # lets a worker register the task modules
)
app.conf.update(
    accept_content=["json"],
    enable_utc=True,
    result_serializer="json",
    task_default_queue="default",
    task_queues=TASK_QUEUES,
    task_serializer="json",
    task_time_limit=TASK_TIME_LIMIT_SECONDS,
    timezone="UTC",
)

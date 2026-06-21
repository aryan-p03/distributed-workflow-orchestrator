from celery import Celery  # type: ignore[import-untyped]

from backend.infrastructure.config import get_settings

settings = get_settings()

celery_app = Celery(
    "backend-worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.task_default_queue = "workflow-tasks"
celery_app.conf.task_track_started = True
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.worker_log_level = settings.celery_log_level.upper()
celery_app.autodiscover_tasks(["backend.worker"])

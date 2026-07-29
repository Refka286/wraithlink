from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "aegispen",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.run_action"],
)
celery_app.conf.task_default_queue = "aegispen"

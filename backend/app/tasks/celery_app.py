from celery import Celery
from app.config import settings

celery = Celery(
    "schedulix",
    broker=settings.effective_redis_url,
    backend=settings.effective_redis_url,
    include=["app.tasks.jobs"]
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.jobs.generate_timetable": {
            "queue": "scheduling"
        },
        "app.tasks.jobs.deliver_notification": {
            "queue": "notifications"
        }
    }
)
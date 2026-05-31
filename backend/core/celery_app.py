import os
from celery import Celery
from celery.schedules import crontab
from core.config import get_settings

settings = get_settings()

broker_url = settings.redis_url
backend_url = settings.redis_url.replace("/0", "/1") if "/0" in settings.redis_url else settings.redis_url

# Override with in-memory broker and backend when running in eager testing mode
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true":
    broker_url = "memory://"
    backend_url = "cache+memory://"

celery_app = Celery(
    "smartonboard",
    broker=broker_url,
    backend=backend_url,
)


celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    result_expires=86400,  # Task result retention set to 24 hours (86400 seconds)
    task_always_eager=os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true",
    task_store_eager_result=True,  # Enables storing task results when eager is True
)

celery_app.conf.beat_schedule = {
    "sweep-sla-breaches-every-30s": {
        "task": "tasks.escalations.check_sla_breaches_task",
        "schedule": 30.0,
    },
    "sweep-approval-escalations-every-30s": {
        "task": "tasks.escalations.check_approval_escalations_task",
        "schedule": 30.0,
    },
    "cleanup-expired-exports-daily": {
        "task": "celery_worker.cleanup_expired_exports_async",
        "schedule": crontab(hour=0, minute=0),
    },
}



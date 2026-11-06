import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("swizzle")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "collect-and-generate-editorial": {
        "task": "newsroom.tasks.poll_and_generate",
        "schedule": crontab(minute="*/15"),
    },
}

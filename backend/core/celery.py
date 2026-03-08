import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "generate-alerts-for-recent-scores-hourly": {
        "task": "alerts.generate_alerts_for_recent_scores",
        "schedule": crontab(minute=0, hour="*"),
        "args": (500,),
    }
}

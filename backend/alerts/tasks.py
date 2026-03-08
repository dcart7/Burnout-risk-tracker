from celery import shared_task

from analytics.models import WeeklyScore
from .services import generate_alerts_for_weekly_score


@shared_task(name="alerts.generate_alerts_for_weekly_score")
def generate_alerts_for_weekly_score_task(weekly_score_id):
    weekly_score = WeeklyScore.objects.select_related("user", "user__team", "submission").get(
        id=weekly_score_id
    )
    return len(generate_alerts_for_weekly_score(weekly_score))


@shared_task(name="alerts.generate_alerts_for_recent_scores")
def generate_alerts_for_recent_scores(limit=500):
    scores = (
        WeeklyScore.objects.select_related("user", "user__team", "submission")
        .filter(burnout_index_stable__isnull=False)
        .order_by("-submission__submitted_at", "-id")[:limit]
    )

    total_created = 0
    for score in scores:
        total_created += len(generate_alerts_for_weekly_score(score))
    return total_created

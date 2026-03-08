from decimal import Decimal, ROUND_HALF_UP

from .models import Alert
from analytics.models import WeeklyScore

HUNDREDTH = Decimal("0.01")
SPIKE_THRESHOLD_PERCENT = Decimal("15")
RISK_THRESHOLD = Decimal("60")


def _compute_delta_percent(previous_value, current_value):
    if previous_value is None or previous_value <= 0:
        return None

    delta = ((current_value - previous_value) / previous_value) * Decimal("100")
    return delta.quantize(HUNDREDTH, rounding=ROUND_HALF_UP)


def _get_previous_stable_index(weekly_score):
    previous_score = (
        WeeklyScore.objects.filter(
            user=weekly_score.user,
            burnout_index_stable__isnull=False,
            submission__submitted_at__lt=weekly_score.submission.submitted_at,
        )
        .order_by("-submission__submitted_at", "-id")
        .first()
    )

    if previous_score is None:
        previous_score = (
            WeeklyScore.objects.filter(
                user=weekly_score.user,
                burnout_index_stable__isnull=False,
                submission__submitted_at=weekly_score.submission.submitted_at,
                id__lt=weekly_score.id,
            )
            .order_by("-id")
            .first()
        )

    return None if previous_score is None else previous_score.burnout_index_stable


def generate_alerts_for_weekly_score(weekly_score):
    if weekly_score.burnout_index_stable is None:
        return []

    current_value = Decimal(weekly_score.burnout_index_stable)
    previous_value = _get_previous_stable_index(weekly_score)
    created_alerts = []

    if current_value > RISK_THRESHOLD:
        threshold_alert, created = Alert.objects.get_or_create(
            weekly_score=weekly_score,
            alert_type=Alert.Type.THRESHOLD,
            defaults={
                "user": weekly_score.user,
                "team": weekly_score.user.team,
                "previous_value": previous_value,
                "current_value": current_value,
                "delta_percent": _compute_delta_percent(previous_value, current_value),
            },
        )
        if created:
            created_alerts.append(threshold_alert)

    delta_percent = _compute_delta_percent(previous_value, current_value)
    if delta_percent is not None and delta_percent > SPIKE_THRESHOLD_PERCENT:
        spike_alert, created = Alert.objects.get_or_create(
            weekly_score=weekly_score,
            alert_type=Alert.Type.SPIKE,
            defaults={
                "user": weekly_score.user,
                "team": weekly_score.user.team,
                "previous_value": previous_value,
                "current_value": current_value,
                "delta_percent": delta_percent,
            },
        )
        if created:
            created_alerts.append(spike_alert)

    return created_alerts

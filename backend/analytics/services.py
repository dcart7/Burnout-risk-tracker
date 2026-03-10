from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count, Max, OuterRef, Subquery

from .cache import (
    get_cached_company_metrics,
    get_cached_team_analytics,
    set_cached_company_metrics,
    set_cached_team_analytics,
)
from .models import WeeklyScore
from alerts.models import Alert
from surveys.models import Question
from users.models import Team, User

THREE_WEEK_WINDOW = 3
HUNDREDTH = Decimal("0.01")
MIN_TEAM_SIZE = 3
MIN_COMPANY_SIZE = 3
LOW_RISK_UPPER_BOUND = Decimal("30")
HIGH_RISK_LOWER_BOUND = Decimal("60")
HUNDRED = Decimal("100")


def calculate_dimension_scores(submission):
    answers = submission.answers.select_related("question")
    scores_by_category = {category: [] for category in Question.Category.values}

    for answer in answers:
        scores_by_category[answer.question.category].append(answer.score)

    averages = {}
    for category, scores in scores_by_category.items():
        if len(scores) != 2:
            raise ValueError(
                f"Expected exactly 2 answers for category '{category}', got {len(scores)}."
            )
        averages[category] = Decimal(sum(scores)) / Decimal("2")

    weekly_score, _ = WeeklyScore.objects.update_or_create(
        submission=submission,
        defaults={
            "user": submission.user,
            "week_number": submission.week_number,
            "stress": averages[Question.Category.STRESS],
            "workload": averages[Question.Category.WORKLOAD],
            "motivation": averages[Question.Category.MOTIVATION],
            "energy": averages[Question.Category.ENERGY],
        },
    )
    return weekly_score


def calculate_burnout_index(weekly_score):
    burnout_index = (
        Decimal("3.5") * weekly_score.stress
        + Decimal("2.5") * weekly_score.workload
        - Decimal("2") * weekly_score.motivation
        - Decimal("2") * weekly_score.energy
        + Decimal("40")
    ).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)
    weekly_score.burnout_index = burnout_index
    weekly_score.save(update_fields=["burnout_index", "updated_at"])
    return burnout_index


def apply_stability_layer(weekly_score, window_size=THREE_WEEK_WINDOW):
    recent_scores = list(
        WeeklyScore.objects.filter(user=weekly_score.user, burnout_index__isnull=False)
        .order_by("-submission__submitted_at", "-id")[:window_size]
    )
    if not recent_scores:
        raise ValueError("Stability layer requires at least one burnout index value.")

    stable_value = (
        sum((score.burnout_index for score in recent_scores), Decimal("0"))
        / Decimal(len(recent_scores))
    ).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)
    weekly_score.burnout_index_stable = stable_value
    weekly_score.save(update_fields=["burnout_index_stable", "updated_at"])
    return stable_value


def calculate_burnout_index_with_stability(submission):
    weekly_score = calculate_dimension_scores(submission)
    calculate_burnout_index(weekly_score)
    apply_stability_layer(weekly_score)
    return weekly_score


def get_team_analytics_for_manager(manager, team_id=None, min_team_size=MIN_TEAM_SIZE):
    managed_teams = Team.objects.filter(manager=manager).order_by("id")
    if team_id is not None:
        managed_teams = managed_teams.filter(id=team_id)

    team = managed_teams.first()
    if not team:
        raise ValueError("Team not found or not managed by this manager.")

    cached = get_cached_team_analytics(team.id)
    if cached is not None:
        return cached

    latest_score_subquery = (
        WeeklyScore.objects.filter(user=OuterRef("pk"), burnout_index_stable__isnull=False)
        .order_by("-submission__submitted_at", "-id")
        .values("burnout_index_stable")[:1]
    )
    latest_indices = list(
        team.members.annotate(latest_burnout_index=Subquery(latest_score_subquery))
        .filter(latest_burnout_index__isnull=False)
        .values_list("latest_burnout_index", flat=True)
    )
    team_size = len(latest_indices)

    if team_size < min_team_size:
        data = {
            "is_hidden": True,
            "reason": "not_enough_data",
            "min_required": min_team_size,
            "team_id": team.id,
            "team_name": team.name,
            "team_size": team_size,
        }
        set_cached_team_analytics(team.id, data)
        return data

    average_index = _calculate_average(latest_indices)
    risk_distribution = _build_risk_distribution(latest_indices, team_size)
    trend = _build_team_trend(team)
    alert_summary = _build_alert_summary(Alert.objects.filter(team=team))

    data = {
        "is_hidden": False,
        "team_id": team.id,
        "team_name": team.name,
        "team_size": team_size,
        "avg_burnout_index": average_index,
        "risk_distribution": risk_distribution,
        "trend": trend,
        "alert_summary": alert_summary,
    }
    set_cached_team_analytics(team.id, data)
    return data


def get_employee_dashboard(user, trend_weeks=8):
    score_queryset = (
        WeeklyScore.objects.filter(user=user, burnout_index_stable__isnull=False)
        .select_related("submission")
        .order_by("-submission__submitted_at", "-id")
    )
    latest_score = score_queryset.first()
    trend_scores = list(score_queryset[:trend_weeks])
    trend_scores.reverse()

    if latest_score is None:
        return {
            "current_index": None,
            "risk_level": None,
            "trend": [],
            "radar": None,
        }

    return {
        "current_index": float(latest_score.burnout_index_stable),
        "risk_level": _classify_risk(Decimal(latest_score.burnout_index_stable)),
        "trend": [
            {
                "week_number": score.week_number,
                "burnout_index": float(score.burnout_index_stable),
                "submitted_at": score.submission.submitted_at,
            }
            for score in trend_scores
        ],
        "radar": {
            "stress": _to_percent(score=latest_score.stress),
            "workload": _to_percent(score=latest_score.workload),
            "motivation": _to_percent(score=latest_score.motivation),
            "energy": _to_percent(score=latest_score.energy),
        },
    }


def get_company_analytics(min_company_size=MIN_COMPANY_SIZE):
    cached = get_cached_company_metrics()
    if cached is not None:
        return cached

    latest_score_subquery = (
        WeeklyScore.objects.filter(user=OuterRef("pk"), burnout_index_stable__isnull=False)
        .order_by("-submission__submitted_at", "-id")
        .values("burnout_index_stable")[:1]
    )
    company_indices = list(
        User.objects.filter(role=User.Role.EMPLOYEE)
        .annotate(latest_burnout_index=Subquery(latest_score_subquery))
        .filter(latest_burnout_index__isnull=False)
        .values_list("latest_burnout_index", flat=True)
    )
    company_size = len(company_indices)
    if company_size < min_company_size:
        data = {
            "is_hidden": True,
            "reason": "not_enough_data",
            "min_required": min_company_size,
            "company_size": company_size,
        }
        set_cached_company_metrics(data)
        return data

    employee_scores = WeeklyScore.objects.filter(
        user__role=User.Role.EMPLOYEE,
        burnout_index_stable__isnull=False,
    )
    team_breakdown = (
        employee_scores.values("user__team_id", "user__team__name")
        .annotate(
            avg_burnout_index=Avg("burnout_index_stable"),
            sample_size=Count("id"),
        )
        .order_by("user__team_id")
    )

    data = {
        "is_hidden": False,
        "company_size": company_size,
        "avg_burnout_index": _calculate_average(company_indices),
        "risk_distribution": _build_risk_distribution(company_indices, company_size),
        "trend": _build_company_trend(employee_scores),
        "alert_summary": _build_alert_summary(Alert.objects.all()),
        "team_breakdown": [
            {
                "team_id": row["user__team_id"],
                "team_name": row["user__team__name"] or "Unassigned",
                "avg_burnout_index": float(
                    Decimal(row["avg_burnout_index"]).quantize(
                        HUNDREDTH, rounding=ROUND_HALF_UP
                    )
                ),
                "sample_size": row["sample_size"],
            }
            for row in team_breakdown
        ],
    }
    set_cached_company_metrics(data)
    return data


def _to_percent(score):
    return float((Decimal(score) * Decimal("10")).quantize(HUNDREDTH, rounding=ROUND_HALF_UP))


def _classify_risk(index):
    if index < LOW_RISK_UPPER_BOUND:
        return "low"
    if index < HIGH_RISK_LOWER_BOUND:
        return "medium"
    return "high"


def _calculate_average(indices):
    total = sum((Decimal(index) for index in indices), Decimal("0"))
    return float((total / Decimal(len(indices))).quantize(HUNDREDTH, rounding=ROUND_HALF_UP))


def _build_risk_distribution(indices, sample_size):
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for index in indices:
        risk_counts[_classify_risk(Decimal(index))] += 1

    distribution = {}
    for risk_level, count in risk_counts.items():
        percentage = (Decimal(count) * HUNDRED / Decimal(sample_size)).quantize(
            HUNDREDTH, rounding=ROUND_HALF_UP
        )
        distribution[risk_level] = {"count": count, "percent": float(percentage)}
    return distribution


def _build_team_trend(team, trend_weeks=8):
    trend_rows = list(
        WeeklyScore.objects.filter(user__team=team, burnout_index_stable__isnull=False)
        .values("week_number")
        .annotate(
            avg_burnout_index=Avg("burnout_index_stable"),
            sample_size=Count("id"),
            latest_submission=Max("submission__submitted_at"),
        )
        .order_by("-latest_submission")[:trend_weeks]
    )
    trend_rows.reverse()
    return [
        {
            "week_number": row["week_number"],
            "avg_burnout_index": float(
                Decimal(row["avg_burnout_index"]).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)
            ),
            "sample_size": row["sample_size"],
        }
        for row in trend_rows
    ]


def _build_company_trend(employee_scores, trend_weeks=8):
    trend_rows = list(
        employee_scores.values("week_number")
        .annotate(
            avg_burnout_index=Avg("burnout_index_stable"),
            sample_size=Count("id"),
            latest_submission=Max("submission__submitted_at"),
        )
        .order_by("-latest_submission")[:trend_weeks]
    )
    trend_rows.reverse()
    return [
        {
            "week_number": row["week_number"],
            "avg_burnout_index": float(
                Decimal(row["avg_burnout_index"]).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)
            ),
            "sample_size": row["sample_size"],
        }
        for row in trend_rows
    ]


def _build_alert_summary(alert_queryset):
    counts = alert_queryset.values("status", "alert_type").annotate(total=Count("id"))
    summary = {
        "total": 0,
        "by_status": {
            Alert.Status.NEW: 0,
            Alert.Status.ACKNOWLEDGED: 0,
            Alert.Status.RESOLVED: 0,
        },
        "by_type": {
            Alert.Type.SPIKE: 0,
            Alert.Type.THRESHOLD: 0,
        },
    }
    for row in counts:
        summary["total"] += row["total"]
        summary["by_status"][row["status"]] += row["total"]
        summary["by_type"][row["alert_type"]] += row["total"]
    return summary

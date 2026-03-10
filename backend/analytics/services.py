from decimal import Decimal, ROUND_HALF_UP

from django.db.models import OuterRef, Subquery
from django.contrib.auth import get_user_model

from .models import WeeklyScore
from surveys.models import Question
from users.models import Team
from .cache import (
    get_cached_team_analytics,
    set_cached_team_analytics,
    get_cached_company_metrics,
    set_cached_company_metrics,
)

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

    average_index = _calculate_average(latest_indices, team_size)
    risk_distribution = _build_risk_distribution(latest_indices, team_size)

    data = {
        "is_hidden": False,
        "team_id": team.id,
        "team_name": team.name,
        "team_size": team_size,
        "avg_burnout_index": float(average_index),
        "risk_distribution": risk_distribution,
    }
    set_cached_team_analytics(team.id, data)
    return data


def get_company_metrics(min_company_size=MIN_COMPANY_SIZE):
    cached = get_cached_company_metrics()
    if cached is not None:
        return cached

    user_model = get_user_model()
    latest_score_subquery = (
        WeeklyScore.objects.filter(user=OuterRef("pk"), burnout_index_stable__isnull=False)
        .order_by("-submission__submitted_at", "-id")
        .values("burnout_index_stable")[:1]
    )
    latest_indices = list(
        user_model.objects.annotate(latest_burnout_index=Subquery(latest_score_subquery))
        .filter(latest_burnout_index__isnull=False)
        .values_list("latest_burnout_index", flat=True)
    )
    total_users = len(latest_indices)

    if total_users < min_company_size:
        data = {
            "is_hidden": True,
            "reason": "not_enough_data",
            "min_required": min_company_size,
            "company_size": total_users,
        }
        set_cached_company_metrics(data)
        return data

    average_index = _calculate_average(latest_indices, total_users)
    risk_distribution = _build_risk_distribution(latest_indices, total_users)

    data = {
        "is_hidden": False,
        "company_size": total_users,
        "avg_burnout_index": float(average_index),
        "risk_distribution": risk_distribution,
    }
    set_cached_company_metrics(data)
    return data


def get_company_analytics(min_company_size=MIN_COMPANY_SIZE):
    return get_company_metrics(min_company_size=min_company_size)


def get_employee_dashboard(user, trend_weeks=8):
    scores = (
        WeeklyScore.objects.filter(user=user, burnout_index_stable__isnull=False)
        .select_related("submission")
        .order_by("-submission__submitted_at", "-id")
    )
    latest_score = scores.first()
    if latest_score is None:
        return {
            "current_index": None,
            "risk_level": None,
            "trend": [],
            "radar": None,
        }

    trend_scores = list(scores[:trend_weeks])
    trend_scores.reverse()

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
            "stress": _to_percent(latest_score.stress),
            "workload": _to_percent(latest_score.workload),
            "motivation": _to_percent(latest_score.motivation),
            "energy": _to_percent(latest_score.energy),
        },
    }


def _calculate_average(values, total):
    total_index = sum((Decimal(value) for value in values), Decimal("0"))
    return (total_index / Decimal(total)).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)


def _build_risk_distribution(values, total):
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for value in values:
        risk_counts[_classify_risk(Decimal(value))] += 1

    risk_distribution = {}
    for risk_level, count in risk_counts.items():
        percentage = (Decimal(count) * HUNDRED / Decimal(total)).quantize(
            HUNDREDTH, rounding=ROUND_HALF_UP
        )
        risk_distribution[risk_level] = {"count": count, "percent": float(percentage)}

    return risk_distribution


def _to_percent(score):
    return float((Decimal(score) * Decimal("10")).quantize(HUNDREDTH, rounding=ROUND_HALF_UP))


def _classify_risk(index):
    if index < LOW_RISK_UPPER_BOUND:
        return "low"
    if index < HIGH_RISK_LOWER_BOUND:
        return "medium"
    return "high"

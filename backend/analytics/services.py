from decimal import Decimal, ROUND_HALF_UP

from .models import WeeklyScore
from surveys.models import Question

THREE_WEEK_WINDOW = 3
HUNDREDTH = Decimal("0.01")


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

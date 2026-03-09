from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from surveys.models import Question, SurveyAnswer, SurveySubmission, SurveyTemplate
from users.models import Team

from .models import WeeklyScore
from .services import (
    apply_stability_layer,
    calculate_burnout_index,
    calculate_dimension_scores,
)


class AnalyticsServicesUnitTestCase(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.manager = self.user_model.objects.create_user(
            username="analytics_manager",
            password="test-pass-123",
            role=self.user_model.Role.MANAGER,
        )
        self.team = Team.objects.create(name="Analytics Team", manager=self.manager)
        self.employee = self.user_model.objects.create_user(
            username="analytics_employee",
            password="test-pass-123",
            role=self.user_model.Role.EMPLOYEE,
            team=self.team,
        )
        self.template = SurveyTemplate.objects.create(version=999, is_active=False)

    def _create_submission_with_answers(self, scores_by_category):
        submission = SurveySubmission.objects.create(
            user=self.employee,
            template=self.template,
            week_number=10,
        )
        position = 1
        for category in Question.Category.values:
            for score in scores_by_category[category]:
                question = Question.objects.create(
                    text=f"{category}-{position}",
                    category=category,
                )
                SurveyAnswer.objects.create(
                    submission=submission,
                    question=question,
                    score=score,
                )
                position += 1
        return submission

    def _create_weekly_score(self, burnout_index, submitted_at):
        submission = SurveySubmission.objects.create(
            user=self.employee,
            template=self.template,
            week_number=12,
        )
        SurveySubmission.objects.filter(pk=submission.pk).update(submitted_at=submitted_at)
        submission.refresh_from_db()
        return WeeklyScore.objects.create(
            submission=submission,
            user=self.employee,
            week_number=12,
            stress=Decimal("5.00"),
            workload=Decimal("5.00"),
            motivation=Decimal("5.00"),
            energy=Decimal("5.00"),
            burnout_index=burnout_index,
        )

    def test_calculate_dimension_scores_averages_two_answers_per_category(self):
        submission = self._create_submission_with_answers(
            {
                Question.Category.STRESS: [2, 6],
                Question.Category.WORKLOAD: [4, 8],
                Question.Category.MOTIVATION: [10, 6],
                Question.Category.ENERGY: [1, 5],
            }
        )

        weekly_score = calculate_dimension_scores(submission)

        self.assertEqual(weekly_score.stress, Decimal("4"))
        self.assertEqual(weekly_score.workload, Decimal("6"))
        self.assertEqual(weekly_score.motivation, Decimal("8"))
        self.assertEqual(weekly_score.energy, Decimal("3"))

    def test_calculate_dimension_scores_raises_when_category_has_not_two_answers(self):
        submission = self._create_submission_with_answers(
            {
                Question.Category.STRESS: [2],
                Question.Category.WORKLOAD: [4, 8],
                Question.Category.MOTIVATION: [10, 6],
                Question.Category.ENERGY: [1, 5],
            }
        )

        with self.assertRaisesMessage(ValueError, "Expected exactly 2 answers"):
            calculate_dimension_scores(submission)

    def test_calculate_burnout_index_applies_formula(self):
        weekly_score = WeeklyScore.objects.create(
            submission=SurveySubmission.objects.create(
                user=self.employee,
                template=self.template,
                week_number=11,
            ),
            user=self.employee,
            week_number=11,
            stress=Decimal("4.00"),
            workload=Decimal("6.00"),
            motivation=Decimal("8.00"),
            energy=Decimal("3.00"),
        )

        burnout_index = calculate_burnout_index(weekly_score)
        weekly_score.refresh_from_db()

        self.assertEqual(burnout_index, Decimal("47.00"))
        self.assertEqual(weekly_score.burnout_index, Decimal("47.00"))

    def test_apply_stability_layer_uses_three_most_recent_scores(self):
        now = timezone.now()
        self._create_weekly_score(Decimal("10.00"), now - timedelta(days=21))
        self._create_weekly_score(Decimal("20.00"), now - timedelta(days=14))
        self._create_weekly_score(Decimal("40.00"), now - timedelta(days=7))
        newest = self._create_weekly_score(Decimal("70.00"), now)

        stable_value = apply_stability_layer(newest)
        newest.refresh_from_db()

        self.assertEqual(stable_value, Decimal("43.33"))
        self.assertEqual(newest.burnout_index_stable, Decimal("43.33"))

    def test_apply_stability_layer_raises_when_no_burnout_index_values_exist(self):
        submission = SurveySubmission.objects.create(
            user=self.employee,
            template=self.template,
            week_number=13,
        )
        weekly_score = WeeklyScore.objects.create(
            submission=submission,
            user=self.employee,
            week_number=13,
            stress=Decimal("5.00"),
            workload=Decimal("5.00"),
            motivation=Decimal("5.00"),
            energy=Decimal("5.00"),
            burnout_index=None,
        )

        with self.assertRaisesMessage(
            ValueError, "Stability layer requires at least one burnout index value."
        ):
            apply_stability_layer(weekly_score)

    def test_apply_stability_layer_with_less_than_window_uses_available_scores(self):
        now = timezone.now()
        self._create_weekly_score(Decimal("60.00"), now - timedelta(days=7))
        newest = self._create_weekly_score(Decimal("12.00"), now)

        stable_value = apply_stability_layer(newest)

        self.assertEqual(stable_value, Decimal("36.00"))

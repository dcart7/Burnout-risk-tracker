from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from analytics.models import WeeklyScore
from surveys.models import SurveySubmission, SurveyTemplate
from users.models import Team

from .models import Alert
from .services import generate_alerts_for_weekly_score
from .tasks import generate_alerts_for_weekly_score_task


class AlertGenerationTestCase(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.manager = self.user_model.objects.create_user(
            username="alerts_manager",
            password="test-pass-123",
            role=self.user_model.Role.MANAGER,
        )
        self.team = Team.objects.create(name="Alerts Team", manager=self.manager)
        self.employee = self.user_model.objects.create_user(
            username="alerts_employee",
            password="test-pass-123",
            team=self.team,
            role=self.user_model.Role.EMPLOYEE,
        )
        self.template = SurveyTemplate.objects.create(version=777, is_active=False)

    def _create_weekly_score(self, stable_index):
        submission = SurveySubmission.objects.create(
            user=self.employee,
            template=self.template,
            week_number=15,
        )
        return WeeklyScore.objects.create(
            submission=submission,
            user=self.employee,
            week_number=15,
            stress=Decimal("5.00"),
            workload=Decimal("5.00"),
            motivation=Decimal("5.00"),
            energy=Decimal("5.00"),
            burnout_index=Decimal(stable_index),
            burnout_index_stable=Decimal(stable_index),
        )

    def _create_weekly_score_with_time(self, stable_index, submitted_at):
        submission = SurveySubmission.objects.create(
            user=self.employee,
            template=self.template,
            week_number=15,
        )
        SurveySubmission.objects.filter(pk=submission.pk).update(submitted_at=submitted_at)
        submission.refresh_from_db()
        return WeeklyScore.objects.create(
            submission=submission,
            user=self.employee,
            week_number=15,
            stress=Decimal("5.00"),
            workload=Decimal("5.00"),
            motivation=Decimal("5.00"),
            energy=Decimal("5.00"),
            burnout_index=Decimal(stable_index),
            burnout_index_stable=Decimal(stable_index),
        )

    def test_generates_threshold_alert_when_index_above_60(self):
        score = self._create_weekly_score("61.00")

        created = generate_alerts_for_weekly_score(score)

        self.assertEqual(len(created), 1)
        alert = Alert.objects.get(weekly_score=score)
        self.assertEqual(alert.alert_type, Alert.Type.THRESHOLD)
        self.assertEqual(alert.current_value, Decimal("61.00"))

    def test_generates_spike_alert_when_increase_exceeds_15_percent(self):
        self._create_weekly_score("40.00")
        score = self._create_weekly_score("50.00")

        created = generate_alerts_for_weekly_score(score)

        self.assertEqual(len(created), 1)
        alert = Alert.objects.get(weekly_score=score, alert_type=Alert.Type.SPIKE)
        self.assertEqual(alert.delta_percent, Decimal("25.00"))

    def test_generates_both_alerts_when_both_conditions_match(self):
        self._create_weekly_score("40.00")
        score = self._create_weekly_score("70.00")

        created = generate_alerts_for_weekly_score(score)

        self.assertEqual(len(created), 2)
        self.assertEqual(Alert.objects.filter(weekly_score=score).count(), 2)

    def test_does_not_duplicate_alerts_for_same_score(self):
        self._create_weekly_score("40.00")
        score = self._create_weekly_score("70.00")

        generate_alerts_for_weekly_score(score)
        generate_alerts_for_weekly_score(score)

        self.assertEqual(Alert.objects.filter(weekly_score=score).count(), 2)

    def test_celery_task_creates_alerts(self):
        self._create_weekly_score("40.00")
        score = self._create_weekly_score("70.00")

        created_count = generate_alerts_for_weekly_score_task(score.id)

        self.assertEqual(created_count, 2)
        self.assertEqual(Alert.objects.filter(weekly_score=score).count(), 2)

    def test_does_not_generate_threshold_alert_at_exact_boundary_60(self):
        score = self._create_weekly_score("60.00")

        created = generate_alerts_for_weekly_score(score)

        self.assertEqual(created, [])
        self.assertFalse(Alert.objects.filter(weekly_score=score).exists())

    def test_does_not_generate_spike_alert_at_exact_boundary_15_percent(self):
        self._create_weekly_score("40.00")
        score = self._create_weekly_score("46.00")

        created = generate_alerts_for_weekly_score(score)

        self.assertEqual(created, [])
        self.assertFalse(Alert.objects.filter(weekly_score=score).exists())

    def test_does_not_generate_alerts_for_null_stable_index(self):
        submission = SurveySubmission.objects.create(
            user=self.employee,
            template=self.template,
            week_number=15,
        )
        score = WeeklyScore.objects.create(
            submission=submission,
            user=self.employee,
            week_number=15,
            stress=Decimal("5.00"),
            workload=Decimal("5.00"),
            motivation=Decimal("5.00"),
            energy=Decimal("5.00"),
            burnout_index=Decimal("70.00"),
            burnout_index_stable=None,
        )

        created = generate_alerts_for_weekly_score(score)

        self.assertEqual(created, [])
        self.assertFalse(Alert.objects.filter(weekly_score=score).exists())

    def test_does_not_generate_spike_when_previous_value_is_zero(self):
        self._create_weekly_score("0.00")
        score = self._create_weekly_score("70.00")

        created = generate_alerts_for_weekly_score(score)

        self.assertEqual(len(created), 1)
        alert = Alert.objects.get(weekly_score=score)
        self.assertEqual(alert.alert_type, Alert.Type.THRESHOLD)
        self.assertIsNone(alert.delta_percent)

    def test_uses_id_fallback_for_previous_score_with_same_submitted_at(self):
        same_time = timezone.now()
        self._create_weekly_score_with_time("50.00", same_time)
        score = self._create_weekly_score_with_time("70.00", same_time)

        generate_alerts_for_weekly_score(score)

        spike_alert = Alert.objects.get(weekly_score=score, alert_type=Alert.Type.SPIKE)
        self.assertEqual(spike_alert.previous_value, Decimal("50.00"))
        self.assertEqual(spike_alert.delta_percent, Decimal("40.00"))

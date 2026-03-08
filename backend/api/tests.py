from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from analytics.models import WeeklyScore
from surveys.models import SurveySubmission, SurveyTemplate
from users.models import Team


class ManagerAnalyticsAPITestCase(APITestCase):
    def setUp(self):
        self.url = reverse("manager_analytics")
        self.user_model = get_user_model()
        self.manager = self.user_model.objects.create_user(
            username="manager_analytics",
            password="test-pass-123",
            role=self.user_model.Role.MANAGER,
        )
        permission = Permission.objects.get(codename="view_team_analytics")
        self.manager.user_permissions.add(permission)

        self.team = Team.objects.create(name="Engineering", manager=self.manager)
        self.template = SurveyTemplate.objects.create(version=999, is_active=False)

    def _create_member(self, username):
        return self.user_model.objects.create_user(
            username=username,
            password="test-pass-123",
            team=self.team,
            role=self.user_model.Role.EMPLOYEE,
        )

    def _create_weekly_score(self, user, stable_index, submitted_at=None):
        submission = SurveySubmission.objects.create(
            user=user,
            template=self.template,
            week_number=10,
        )
        if submitted_at is not None:
            SurveySubmission.objects.filter(pk=submission.pk).update(submitted_at=submitted_at)

        return WeeklyScore.objects.create(
            submission=submission,
            user=user,
            week_number=10,
            stress=Decimal("5.00"),
            workload=Decimal("5.00"),
            motivation=Decimal("5.00"),
            energy=Decimal("5.00"),
            burnout_index=Decimal(stable_index),
            burnout_index_stable=Decimal(stable_index),
        )

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_requires_view_team_analytics_permission(self):
        user_without_permission = self.user_model.objects.create_user(
            username="manager_without_permission",
            password="test-pass-123",
        )
        self.client.force_authenticate(user_without_permission)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hides_analytics_when_less_than_three_people_with_scores(self):
        member_1 = self._create_member("employee_1")
        member_2 = self._create_member("employee_2")
        self._create_weekly_score(member_1, "10.00")
        self._create_weekly_score(member_2, "45.00")

        self.client.force_authenticate(self.manager)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["is_hidden"])
        self.assertEqual(response.data["reason"], "not_enough_data")
        self.assertEqual(response.data["min_required"], 3)
        self.assertEqual(response.data["team_size"], 2)
        self.assertNotIn("avg_burnout_index", response.data)
        self.assertNotIn("risk_distribution", response.data)

    def test_returns_aggregate_and_risk_distribution_with_threshold_boundaries(self):
        member_1 = self._create_member("employee_low")
        member_2 = self._create_member("employee_medium")
        member_3 = self._create_member("employee_medium_high")
        member_4 = self._create_member("employee_high")
        self._create_weekly_score(member_1, "10.00")
        self._create_weekly_score(member_2, "30.00")
        self._create_weekly_score(member_3, "59.99")
        self._create_weekly_score(member_4, "60.00")

        self.client.force_authenticate(self.manager)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(response.data["is_hidden"])
        self.assertEqual(response.data["team_size"], 4)
        self.assertEqual(response.data["avg_burnout_index"], 40.0)
        self.assertEqual(response.data["risk_distribution"]["low"]["count"], 1)
        self.assertEqual(response.data["risk_distribution"]["medium"]["count"], 2)
        self.assertEqual(response.data["risk_distribution"]["high"]["count"], 1)
        self.assertEqual(response.data["risk_distribution"]["low"]["percent"], 25.0)
        self.assertEqual(response.data["risk_distribution"]["medium"]["percent"], 50.0)
        self.assertEqual(response.data["risk_distribution"]["high"]["percent"], 25.0)

    def test_uses_latest_score_per_member(self):
        member_1 = self._create_member("employee_latest")
        member_2 = self._create_member("employee_mid")
        member_3 = self._create_member("employee_hi")
        now = timezone.now()

        self._create_weekly_score(member_1, "80.00", submitted_at=now - timedelta(days=7))
        self._create_weekly_score(member_1, "20.00", submitted_at=now)
        self._create_weekly_score(member_2, "40.00", submitted_at=now)
        self._create_weekly_score(member_3, "70.00", submitted_at=now)

        self.client.force_authenticate(self.manager)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["team_size"], 3)
        self.assertEqual(response.data["avg_burnout_index"], 43.33)
        self.assertEqual(response.data["risk_distribution"]["low"]["count"], 1)
        self.assertEqual(response.data["risk_distribution"]["medium"]["count"], 1)
        self.assertEqual(response.data["risk_distribution"]["high"]["count"], 1)

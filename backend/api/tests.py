from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from analytics.models import WeeklyScore
from alerts.models import Alert
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


class EmployeeDashboardAPITestCase(APITestCase):
    def setUp(self):
        self.url = reverse("employee_dashboard")
        self.user_model = get_user_model()
        self.employee = self.user_model.objects.create_user(
            username="employee_dashboard",
            password="test-pass-123",
            role=self.user_model.Role.EMPLOYEE,
        )
        permission = Permission.objects.get(codename="view_own_dashboard")
        self.employee.user_permissions.add(permission)
        self.template = SurveyTemplate.objects.create(version=1001, is_active=False)

    def _create_weekly_score(self, user, stable_index, stress, workload, motivation, energy):
        submission = SurveySubmission.objects.create(
            user=user,
            template=self.template,
            week_number=12,
        )
        return WeeklyScore.objects.create(
            submission=submission,
            user=user,
            week_number=12,
            stress=Decimal(stress),
            workload=Decimal(workload),
            motivation=Decimal(motivation),
            energy=Decimal(energy),
            burnout_index=Decimal(stable_index),
            burnout_index_stable=Decimal(stable_index),
        )

    def test_returns_only_own_analytics(self):
        coworker = self.user_model.objects.create_user(
            username="coworker",
            password="test-pass-123",
            role=self.user_model.Role.EMPLOYEE,
        )
        self._create_weekly_score(self.employee, "58.00", "6.00", "5.00", "4.00", "7.00")
        self._create_weekly_score(coworker, "99.00", "9.00", "9.00", "1.00", "1.00")

        self.client.force_authenticate(self.employee)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["current_index"], 58.0)
        self.assertEqual(response.data["risk_level"], "medium")
        self.assertEqual(len(response.data["trend"]), 1)
        self.assertEqual(response.data["trend"][0]["burnout_index"], 58.0)
        self.assertEqual(response.data["radar"]["stress"], 60.0)
        self.assertEqual(response.data["radar"]["workload"], 50.0)
        self.assertEqual(response.data["radar"]["motivation"], 40.0)
        self.assertEqual(response.data["radar"]["energy"], 70.0)
        self.assertIn("weather_summary", response.data)
        self.assertIn("current", response.data["weather_summary"])
        self.assertIn("recommendation", response.data["weather_summary"])

    def test_requires_employee_dashboard_permission(self):
        no_permission_user = self.user_model.objects.create_user(
            username="employee_no_dashboard_permission",
            password="test-pass-123",
            role=self.user_model.Role.EMPLOYEE,
        )
        self.client.force_authenticate(no_permission_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class HRCompanyAnalyticsAPITestCase(APITestCase):
    def setUp(self):
        self.url = reverse("hr_company_analytics")
        self.user_model = get_user_model()
        self.hr_user = self.user_model.objects.create_user(
            username="hr_company",
            password="test-pass-123",
            role=self.user_model.Role.HR,
        )
        permission = Permission.objects.get(codename="view_company_analytics")
        self.hr_user.user_permissions.add(permission)

        manager = self.user_model.objects.create_user(
            username="team_manager",
            password="test-pass-123",
            role=self.user_model.Role.MANAGER,
        )
        self.team = Team.objects.create(name="HR Analytics Team", manager=manager)
        self.template = SurveyTemplate.objects.create(version=1002, is_active=False)

    def _create_employee_score(self, username, index):
        employee = self.user_model.objects.create_user(
            username=username,
            password="test-pass-123",
            role=self.user_model.Role.EMPLOYEE,
            team=self.team,
        )
        submission = SurveySubmission.objects.create(
            user=employee,
            template=self.template,
            week_number=20,
        )
        score = WeeklyScore.objects.create(
            submission=submission,
            user=employee,
            week_number=20,
            stress=Decimal("5.00"),
            workload=Decimal("5.00"),
            motivation=Decimal("5.00"),
            energy=Decimal("5.00"),
            burnout_index=Decimal(index),
            burnout_index_stable=Decimal(index),
        )
        return score

    def test_returns_company_aggregate_without_personal_data(self):
        score_1 = self._create_employee_score("employee_hr_1", "20.00")
        self._create_employee_score("employee_hr_2", "55.00")
        self._create_employee_score("employee_hr_3", "70.00")
        Alert.objects.create(
            weekly_score=score_1,
            user=score_1.user,
            team=score_1.user.team,
            alert_type=Alert.Type.SPIKE,
            previous_value=Decimal("10.00"),
            current_value=Decimal("20.00"),
            delta_percent=Decimal("100.00"),
        )

        self.client.force_authenticate(self.hr_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(response.data["is_hidden"])
        self.assertEqual(response.data["company_size"], 3)
        self.assertEqual(response.data["avg_burnout_index"], 48.33)
        self.assertIn("risk_distribution", response.data)
        self.assertIn("team_breakdown", response.data)
        self.assertIn("alert_summary", response.data)
        self.assertNotIn("users", response.data)
        self.assertEqual(response.data["alert_summary"]["total"], 1)

    def test_requires_hr_company_permission(self):
        user_without_permission = self.user_model.objects.create_user(
            username="hr_no_company_permission",
            password="test-pass-123",
            role=self.user_model.Role.HR,
        )
        self.client.force_authenticate(user_without_permission)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CompanyMetricsAPITestCase(APITestCase):
    def setUp(self):
        self.url = reverse("company_metrics")
        self.user_model = get_user_model()
        self.hr_user = self.user_model.objects.create_user(
            username="company_hr",
            password="test-pass-123",
            role=self.user_model.Role.HR,
        )
        permission = Permission.objects.get(codename="view_company_analytics")
        self.hr_user.user_permissions.add(permission)

        self.template = SurveyTemplate.objects.create(version=998, is_active=False)

    def _create_employee(self, username):
        return self.user_model.objects.create_user(
            username=username,
            password="test-pass-123",
            role=self.user_model.Role.EMPLOYEE,
        )

    def _create_weekly_score(self, user, stable_index, submitted_at=None):
        submission = SurveySubmission.objects.create(
            user=user,
            template=self.template,
            week_number=9,
        )
        if submitted_at is not None:
            SurveySubmission.objects.filter(pk=submission.pk).update(submitted_at=submitted_at)

        return WeeklyScore.objects.create(
            submission=submission,
            user=user,
            week_number=9,
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

    def test_requires_view_company_analytics_permission(self):
        user_without_permission = self.user_model.objects.create_user(
            username="no_company_permission",
            password="test-pass-123",
        )
        self.client.force_authenticate(user_without_permission)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_company_metrics(self):
        employee_1 = self._create_employee("company_low")
        employee_2 = self._create_employee("company_medium")
        employee_3 = self._create_employee("company_high")
        self._create_weekly_score(employee_1, "20.00")
        self._create_weekly_score(employee_2, "45.00")
        self._create_weekly_score(employee_3, "70.00")

        self.client.force_authenticate(self.hr_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(response.data["is_hidden"])
        self.assertEqual(response.data["company_size"], 3)
        self.assertEqual(response.data["risk_distribution"]["low"]["count"], 1)
        self.assertEqual(response.data["risk_distribution"]["medium"]["count"], 1)
        self.assertEqual(response.data["risk_distribution"]["high"]["count"], 1)

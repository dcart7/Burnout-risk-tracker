import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from analytics.models import WeeklyScore
from .models import Question, SurveyTemplate, SurveyTemplateQuestion, SurveySubmission, SurveyAnswer


class QuestionPoolAPITestCase(APITestCase):
    def setUp(self):
        self.pool_url = reverse("question-pool")
        self.hr_user = get_user_model().objects.create_user(
            username="hr_manager",
            password="test-pass-123",
        )
        manage_question_bank = Permission.objects.get(codename="manage_question_bank")
        self.hr_user.user_permissions.add(manage_question_bank)

        self.user = get_user_model().objects.create_user(
            username="employee",
            password="test-pass-123",
        )

        self.active_stress_question = Question.objects.create(
            text="Active stress question",
            category=Question.Category.STRESS,
            is_active=True,
        )
        Question.objects.create(
            text="Inactive stress question",
            category=Question.Category.STRESS,
            is_active=False,
        )
        self.active_energy_question = Question.objects.create(
            text="Active energy question",
            category=Question.Category.ENERGY,
            is_active=True,
        )

    def test_pool_requires_authentication(self):
        response = self.client.get(self.pool_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pool_returns_only_active_questions_grouped_by_category(self):
        self.client.force_authenticate(self.hr_user)
        response = self.client.get(self.pool_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            {item["id"] for item in response.data["results"]},
            {self.active_stress_question.id, self.active_energy_question.id},
        )

        self.assertIn(Question.Category.STRESS, response.data["by_category"])
        self.assertIn(Question.Category.WORKLOAD, response.data["by_category"])
        self.assertIn(Question.Category.MOTIVATION, response.data["by_category"])
        self.assertIn(Question.Category.ENERGY, response.data["by_category"])
        self.assertEqual(len(response.data["by_category"][Question.Category.STRESS]), 1)
        self.assertEqual(len(response.data["by_category"][Question.Category.ENERGY]), 1)
        self.assertEqual(len(response.data["by_category"][Question.Category.WORKLOAD]), 0)
        self.assertEqual(len(response.data["by_category"][Question.Category.MOTIVATION]), 0)

    def test_pool_allows_filter_by_category(self):
        self.client.force_authenticate(self.hr_user)
        response = self.client.get(self.pool_url, {"category": Question.Category.STRESS})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.active_stress_question.id)

    def test_pool_denies_employee_without_hr_permission(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.pool_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_question_create_not_allowed_for_hr(self):
        self.client.force_authenticate(self.hr_user)
        response = self.client.post(
            reverse("question-list"),
            {"text": "New question", "category": Question.Category.STRESS, "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Question.objects.filter(text="New question").count(), 0)

    def test_question_create_denied_for_employee_without_hr_permission(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("question-list"),
            {"text": "New question", "category": Question.Category.STRESS, "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ImportQuestionsCommandTestCase(TestCase):
    def test_import_questions_from_csv(self):
        csv_content = (
            "text,category,is_active\n"
            "\"Question A\",stress,true\n"
            "\"Question B\",energy,false\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as temp_file:
            temp_file.write(csv_content)
            temp_csv_path = temp_file.name

        try:
            call_command("import_questions", temp_csv_path)

            self.assertEqual(Question.objects.count(), 2)
            self.assertTrue(
                Question.objects.filter(
                    text="Question A", category=Question.Category.STRESS
                ).exists()
            )
            self.assertTrue(
                Question.objects.filter(
                    text="Question B", category=Question.Category.ENERGY, is_active=False
                ).exists()
            )
        finally:
            Path(temp_csv_path).unlink(missing_ok=True)


class WeeklySurveySubmissionAPITestCase(APITestCase):
    def setUp(self):
        self.url = reverse("weekly-survey-submit")
        self.user = get_user_model().objects.create_user(
            username="employee_submitter",
            password="test-pass-123",
        )
        permission = Permission.objects.get(codename="answer_weekly_survey")
        self.user.user_permissions.add(permission)

        categories = [
            Question.Category.STRESS,
            Question.Category.STRESS,
            Question.Category.WORKLOAD,
            Question.Category.WORKLOAD,
            Question.Category.MOTIVATION,
            Question.Category.MOTIVATION,
            Question.Category.ENERGY,
            Question.Category.ENERGY,
        ]
        self.questions = []
        for index, category in enumerate(categories, start=1):
            question = Question.objects.create(
                text=f"Question {index} ({category})",
                category=category,
                is_active=True,
            )
            self.questions.append(question)

        self.active_template = SurveyTemplate.objects.create(version=1, is_active=True)
        for position, question in enumerate(self.questions, start=1):
            SurveyTemplateQuestion.objects.create(
                template=self.active_template,
                question=question,
                position=position,
            )

    def _valid_payload(self):
        return {
            "answers": [
                {"question_id": question.id, "score": (index % 10) + 1}
                for index, question in enumerate(self.questions, start=1)
            ]
        }

    def _payload_for_dimensions(self, stress, workload, motivation, energy):
        return {
            "answers": [
                {"question_id": self.questions[0].id, "score": stress},
                {"question_id": self.questions[1].id, "score": stress},
                {"question_id": self.questions[2].id, "score": workload},
                {"question_id": self.questions[3].id, "score": workload},
                {"question_id": self.questions[4].id, "score": motivation},
                {"question_id": self.questions[5].id, "score": motivation},
                {"question_id": self.questions[6].id, "score": energy},
                {"question_id": self.questions[7].id, "score": energy},
            ]
        }

    def test_requires_authentication(self):
        response = self.client.post(self.url, self._valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_requires_answer_weekly_survey_permission(self):
        user_without_permission = get_user_model().objects.create_user(
            username="employee_no_perm",
            password="test-pass-123",
        )
        self.client.force_authenticate(user_without_permission)
        response = self.client.post(self.url, self._valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creates_submission_with_8_answers(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, self._valid_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SurveySubmission.objects.count(), 1)
        submission = SurveySubmission.objects.first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.user, self.user)
        self.assertEqual(submission.template, self.active_template)
        self.assertGreaterEqual(submission.week_number, 1)
        self.assertLessEqual(submission.week_number, 53)
        self.assertEqual(response.data["week_number"], submission.week_number)
        self.assertEqual(SurveyAnswer.objects.filter(submission=submission).count(), 8)
        self.assertTrue(WeeklyScore.objects.filter(submission=submission).exists())

    def test_calculates_dimension_scores_and_saves_weekly_score(self):
        self.client.force_authenticate(self.user)
        payload = {
            "answers": [
                {"question_id": self.questions[0].id, "score": 2},  # stress
                {"question_id": self.questions[1].id, "score": 6},  # stress
                {"question_id": self.questions[2].id, "score": 4},  # workload
                {"question_id": self.questions[3].id, "score": 8},  # workload
                {"question_id": self.questions[4].id, "score": 10},  # motivation
                {"question_id": self.questions[5].id, "score": 6},  # motivation
                {"question_id": self.questions[6].id, "score": 1},  # energy
                {"question_id": self.questions[7].id, "score": 5},  # energy
            ]
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        submission = SurveySubmission.objects.get(pk=response.data["submission_id"])
        weekly_score = WeeklyScore.objects.get(submission=submission)
        self.assertEqual(weekly_score.user, self.user)
        self.assertEqual(weekly_score.week_number, submission.week_number)
        self.assertEqual(float(weekly_score.stress), 4.0)
        self.assertEqual(float(weekly_score.workload), 6.0)
        self.assertEqual(float(weekly_score.motivation), 8.0)
        self.assertEqual(float(weekly_score.energy), 3.0)
        self.assertEqual(float(weekly_score.burnout_index), 47.0)
        self.assertEqual(float(weekly_score.burnout_index_stable), 47.0)
        self.assertEqual(response.data["dimension_scores_percent"]["stress"], 40.0)
        self.assertEqual(response.data["dimension_scores_percent"]["workload"], 60.0)
        self.assertEqual(response.data["dimension_scores_percent"]["motivation"], 80.0)
        self.assertEqual(response.data["dimension_scores_percent"]["energy"], 30.0)
        self.assertEqual(response.data["burnout_index_percent"], 47.0)
        self.assertEqual(response.data["burnout_index_stable_percent"], 47.0)
        self.assertTrue(all("score_percent" in item for item in response.data["answers"]))
        self.assertTrue(
            all(0.0 <= item["score_percent"] <= 100.0 for item in response.data["answers"])
        )

    def test_applies_three_week_moving_average_stability_layer(self):
        self.client.force_authenticate(self.user)

        payload_week_1 = self._payload_for_dimensions(
            stress=10, workload=10, motivation=10, energy=10
        )
        payload_week_2 = self._payload_for_dimensions(
            stress=2, workload=2, motivation=10, energy=10
        )
        payload_week_3 = self._payload_for_dimensions(
            stress=10, workload=10, motivation=0, energy=0
        )

        response_1 = self.client.post(self.url, payload_week_1, format="json")
        response_2 = self.client.post(self.url, payload_week_2, format="json")
        response_3 = self.client.post(self.url, payload_week_3, format="json")

        self.assertEqual(response_1.status_code, status.HTTP_201_CREATED, response_1.data)
        self.assertEqual(response_2.status_code, status.HTTP_201_CREATED, response_2.data)
        self.assertEqual(response_3.status_code, status.HTTP_201_CREATED, response_3.data)

        score_1 = WeeklyScore.objects.get(submission_id=response_1.data["submission_id"])
        score_2 = WeeklyScore.objects.get(submission_id=response_2.data["submission_id"])
        score_3 = WeeklyScore.objects.get(submission_id=response_3.data["submission_id"])

        self.assertEqual(score_1.burnout_index, Decimal("60.00"))
        self.assertEqual(score_1.burnout_index_stable, Decimal("60.00"))

        self.assertEqual(score_2.burnout_index, Decimal("12.00"))
        self.assertEqual(score_2.burnout_index_stable, Decimal("36.00"))

        self.assertEqual(score_3.burnout_index, Decimal("100.00"))
        self.assertEqual(score_3.burnout_index_stable, Decimal("57.33"))

    def test_rejects_if_answers_count_is_not_8(self):
        self.client.force_authenticate(self.user)
        payload = self._valid_payload()
        payload["answers"] = payload["answers"][:7]

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exactly 8 answers", str(response.data))

    def test_rejects_if_category_distribution_is_not_2_per_category(self):
        self.client.force_authenticate(self.user)
        payload = self._valid_payload()
        energy_question = self.questions[-1]
        energy_question.category = Question.Category.STRESS
        energy_question.save(update_fields=["category"])

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("2 answered questions per category", str(response.data))

    def test_accepts_score_zero(self):
        self.client.force_authenticate(self.user)
        payload = self._valid_payload()
        payload["answers"][0]["score"] = 0

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_rejects_score_below_zero(self):
        self.client.force_authenticate(self.user)
        payload = self._valid_payload()
        payload["answers"][0]["score"] = -1

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("score", str(response.data))

    def test_rejects_score_above_ten(self):
        self.client.force_authenticate(self.user)
        payload = self._valid_payload()
        payload["answers"][0]["score"] = 11
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("score", str(response.data))

    @patch("surveys.serializers.generate_alerts_for_weekly_score_task.delay")
    @patch("surveys.serializers.transaction.on_commit")
    def test_triggers_background_alert_generation_after_submission(
        self, mocked_on_commit, mocked_delay
    ):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, self._valid_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(mocked_on_commit.call_count, 2)
        for call_args in mocked_on_commit.call_args_list:
            on_commit_callback = call_args.args[0]
            on_commit_callback()
        mocked_delay.assert_called_once()


class SurveyTemplateVersioningAPITestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="hr_template_manager",
            password="test-pass-123",
        )
        manage_templates = Permission.objects.get(codename="manage_survey_templates")
        self.user.user_permissions.add(manage_templates)

        self.questions = []
        index = 1
        for category in (
            Question.Category.STRESS,
            Question.Category.WORKLOAD,
            Question.Category.MOTIVATION,
            Question.Category.ENERGY,
        ):
            for _ in range(25):
                self.questions.append(
                    Question.objects.create(
                        text=f"Question bank item {index}",
                        category=category,
                        is_active=True,
                    )
                )
                index += 1

        self.template = SurveyTemplate.objects.create(version=1, is_active=True)
        initial_questions = []
        for category in (
            Question.Category.STRESS,
            Question.Category.WORKLOAD,
            Question.Category.MOTIVATION,
            Question.Category.ENERGY,
        ):
            initial_questions.extend(
                list(Question.objects.filter(category=category, is_active=True).order_by("id")[:2])
            )
        for position, question in enumerate(initial_questions, start=1):
            SurveyTemplateQuestion.objects.create(
                template=self.template,
                question=question,
                position=position,
            )

        self.url = reverse("survey-template-detail", args=[self.template.id])

    def test_update_creates_new_template_version(self):
        self.client.force_authenticate(self.user)
        replacement_questions = []
        for category in (
            Question.Category.STRESS,
            Question.Category.WORKLOAD,
            Question.Category.MOTIVATION,
            Question.Category.ENERGY,
        ):
            replacement_questions.extend(
                list(
                    Question.objects.filter(category=category, is_active=True).order_by("id")[2:4]
                )
            )
        payload = {
            "is_active": True,
            "template_questions": [
                {"question_id": question.id, "position": idx}
                for idx, question in enumerate(replacement_questions, start=1)
            ],
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(SurveyTemplate.objects.count(), 2)
        self.template.refresh_from_db()
        self.assertFalse(self.template.is_active)

        new_template = SurveyTemplate.objects.order_by("-version").first()
        self.assertEqual(new_template.version, 2)
        self.assertTrue(new_template.is_active)
        self.assertEqual(new_template.template_questions.count(), 8)
        self.assertEqual(response.data["id"], new_template.id)
        self.assertEqual(response.data["version"], 2)

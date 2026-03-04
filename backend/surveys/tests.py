import tempfile
from pathlib import Path

from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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

    def test_question_create_allowed_for_hr(self):
        self.client.force_authenticate(self.hr_user)
        response = self.client.post(
            reverse("question-list"),
            {"text": "New question", "category": Question.Category.STRESS, "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Question.objects.filter(text="New question").count(), 1)

    def test_question_create_denied_for_employee(self):
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

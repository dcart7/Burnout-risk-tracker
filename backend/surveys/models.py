from django.db import models
from django.core.exceptions import ValidationError


class SurveyTemplate(models.Model):
    version = models.PositiveIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    questions = models.ManyToManyField(
        "Question",
        through="SurveyTemplateQuestion",
        related_name="survey_templates",
        blank=True,
    )

    class Meta:
        db_table = "survey_templates"
        verbose_name = "Survey Template"
        verbose_name_plural = "Survey Templates"

    def clean(self):
        if not self.pk or not self.is_active:
            return

        template_questions = self.template_questions.select_related("question")
        if template_questions.count() != 8:
            raise ValidationError("Active template must contain exactly 8 questions.")

        category_counts = {
            Question.Category.STRESS: 0,
            Question.Category.WORKLOAD: 0,
            Question.Category.MOTIVATION: 0,
            Question.Category.ENERGY: 0,
        }
        for template_question in template_questions:
            category = template_question.question.category
            category_counts[category] += 1

        invalid_categories = [
            category for category, count in category_counts.items() if count != 2
        ]
        if invalid_categories:
            raise ValidationError(
                "Active template must have exactly 2 questions per category."
            )

    def __str__(self):
        return f"Template v{self.version}"


class Question(models.Model):
    class Category(models.TextChoices):
        STRESS = "stress", "Stress"
        WORKLOAD = "workload", "Workload"
        MOTIVATION = "motivation", "Motivation"
        ENERGY = "energy", "Energy"

    text = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "questions"
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def __str__(self):
        return f"{self.get_category_display()}: {self.text[:60]}"


class SurveyTemplateQuestion(models.Model):
    template = models.ForeignKey(
        SurveyTemplate, on_delete=models.CASCADE, related_name="template_questions"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "survey_template_questions"
        verbose_name = "Survey Template Question"
        verbose_name_plural = "Survey Template Questions"
        constraints = [
            models.UniqueConstraint(
                fields=["template", "question"], name="uq_template_question"
            ),
            models.UniqueConstraint(
                fields=["template", "position"], name="uq_template_position"
            ),
            models.CheckConstraint(
                check=models.Q(position__gte=1) & models.Q(position__lte=8),
                name="ck_template_question_position_1_8",
            ),
        ]

    def clean(self):
        if not self.question_id:
            return

        if not self.question.is_active:
            raise ValidationError("Only active questions can be selected.")

        if not self.template_id:
            return

        same_category_count = (
            SurveyTemplateQuestion.objects.select_related("question")
            .filter(template_id=self.template_id, question__category=self.question.category)
            .exclude(pk=self.pk)
            .count()
        )
        if same_category_count >= 2:
            raise ValidationError(
                f"Template can contain only 2 questions from category '{self.question.category}'."
            )

    def __str__(self):
        return f"v{self.template.version} - Q{self.position}"

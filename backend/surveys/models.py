from django.db import models


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

    def __str__(self):
        return f"v{self.template.version} - Q{self.position}"

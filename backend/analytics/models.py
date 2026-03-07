from django.conf import settings
from django.db import models


class WeeklyScore(models.Model):
    submission = models.OneToOneField(
        "surveys.SurveySubmission",
        on_delete=models.CASCADE,
        related_name="weekly_score",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_scores",
    )
    week_number = models.PositiveSmallIntegerField()
    stress = models.DecimalField(max_digits=4, decimal_places=2)
    workload = models.DecimalField(max_digits=4, decimal_places=2)
    motivation = models.DecimalField(max_digits=4, decimal_places=2)
    energy = models.DecimalField(max_digits=4, decimal_places=2)
    burnout_index = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    burnout_index_stable = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "weekly_scores"
        verbose_name = "Weekly Score"
        verbose_name_plural = "Weekly Scores"
        constraints = [
            models.CheckConstraint(
                check=models.Q(week_number__gte=1) & models.Q(week_number__lte=53),
                name="ck_weekly_score_week_number_1_53",
            ),
            models.CheckConstraint(
                check=models.Q(burnout_index__gte=0) & models.Q(burnout_index__lte=100)
                | models.Q(burnout_index__isnull=True),
                name="ck_weekly_score_burnout_index_0_100_or_null",
            ),
            models.CheckConstraint(
                check=models.Q(burnout_index_stable__gte=0)
                & models.Q(burnout_index_stable__lte=100)
                | models.Q(burnout_index_stable__isnull=True),
                name="ck_weekly_score_burnout_index_stable_0_100_or_null",
            ),
        ]

    def __str__(self):
        return f"WeeklyScore #{self.pk} (submission={self.submission_id})"

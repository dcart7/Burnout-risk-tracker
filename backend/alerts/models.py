from django.conf import settings
from django.db import models


class Alert(models.Model):
    class Type(models.TextChoices):
        SPIKE = "spike", "Spike"
        THRESHOLD = "threshold", "Threshold"

    class Status(models.TextChoices):
        NEW = "new", "New"
        ACKNOWLEDGED = "ack", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    weekly_score = models.ForeignKey(
        "analytics.WeeklyScore",
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    team = models.ForeignKey(
        "users.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    alert_type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    previous_value = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=6, decimal_places=2)
    delta_percent = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alerts"
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"
        constraints = [
            models.UniqueConstraint(
                fields=["weekly_score", "alert_type"],
                name="uq_alert_weekly_score_type",
            )
        ]

    def __str__(self):
        return f"Alert #{self.pk} ({self.alert_type}) for user={self.user_id}"

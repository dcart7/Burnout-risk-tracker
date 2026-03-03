from django.contrib.auth.models import AbstractUser
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=120, unique=True)
    manager = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_teams",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams"
        verbose_name = "Team"
        verbose_name_plural = "Teams"

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        MANAGER = "manager", "Manager"
        HR = "hr", "HR"

    # Additional fields for burnout tracking
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="members"
    )
    department = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    years_of_experience = models.IntegerField(null=True, blank=True)
    
    # Risk assessment fields
    burnout_risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        default='low'
    )
    last_assessment_date = models.DateTimeField(null=True, blank=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        permissions = (
            ("answer_weekly_survey", "Can answer weekly survey"),
            ("view_own_dashboard", "Can view own dashboard"),
            ("view_team_analytics", "Can view team analytics"),
            ("receive_team_alerts", "Can receive team alerts"),
            ("manage_question_bank", "Can manage question bank"),
            ("manage_survey_templates", "Can manage survey templates"),
            ("view_company_analytics", "Can view company analytics"),
            ("view_alert_panel", "Can view alert panel"),
        )

    def __str__(self):
        return f"{self.first_name} {self.last_name}" or self.username

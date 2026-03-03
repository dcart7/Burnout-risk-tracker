from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Team, User


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "manager", "created_at")
    search_fields = ("name",)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Burnout Profile",
            {
                "fields": (
                    "role",
                    "team",
                    "department",
                    "position",
                    "years_of_experience",
                    "burnout_risk_level",
                    "last_assessment_date",
                    "email_notifications",
                )
            },
        ),
    )

from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "alert_type",
        "status",
        "user",
        "team",
        "current_value",
        "delta_percent",
        "created_at",
    )
    list_filter = ("alert_type", "status", "team", "created_at")
    search_fields = ("user__username", "team__name")

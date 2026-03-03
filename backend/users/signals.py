from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


ROLE_PERMISSIONS = {
    "Employee": (
        "answer_weekly_survey",
        "view_own_dashboard",
    ),
    "Manager": (
        "view_team_analytics",
        "receive_team_alerts",
        "view_team",
    ),
    "HR": (
        "manage_question_bank",
        "manage_survey_templates",
        "view_company_analytics",
        "view_alert_panel",
        "add_team",
        "change_team",
        "delete_team",
        "view_team",
        "view_user",
    ),
}


@receiver(post_migrate)
def configure_rbac_groups(sender, **kwargs):
    if sender.label != "users":
        return

    for group_name, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permissions = list(Permission.objects.filter(codename__in=codenames))
        group.permissions.set(permissions)

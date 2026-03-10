from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_user_custom_permissions"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={
                "db_table": "users",
                "verbose_name": "User",
                "verbose_name_plural": "Users",
                "permissions": (
                    ("answer_weekly_survey", "Can answer weekly survey"),
                    ("view_own_dashboard", "Can view own dashboard"),
                    ("view_team_analytics", "Can view team analytics"),
                    ("receive_team_alerts", "Can receive team alerts"),
                    ("manage_question_bank", "Can manage question bank"),
                    ("manage_survey_templates", "Can manage survey templates"),
                    ("view_company_analytics", "Can view company analytics"),
                    ("view_alert_panel", "Can view alert panel"),
                    ("view_raw_answers", "Can view raw survey answers"),
                ),
            },
        ),
    ]

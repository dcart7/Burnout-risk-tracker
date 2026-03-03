from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("surveys", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SurveyTemplate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("version", models.PositiveIntegerField(unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_active", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Survey Template",
                "verbose_name_plural": "Survey Templates",
                "db_table": "survey_templates",
            },
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Question",
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
                ("text", models.TextField()),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("stress", "Stress"),
                            ("workload", "Workload"),
                            ("motivation", "Motivation"),
                            ("energy", "Energy"),
                        ],
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Question",
                "verbose_name_plural": "Questions",
                "db_table": "questions",
            },
        ),
    ]

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("surveys", "0002_surveytemplate"),
    ]

    operations = [
        migrations.CreateModel(
            name="SurveyTemplateQuestion",
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
                ("position", models.PositiveSmallIntegerField()),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="surveys.question",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="template_questions",
                        to="surveys.surveytemplate",
                    ),
                ),
            ],
            options={
                "verbose_name": "Survey Template Question",
                "verbose_name_plural": "Survey Template Questions",
                "db_table": "survey_template_questions",
            },
        ),
        migrations.AddField(
            model_name="surveytemplate",
            name="questions",
            field=models.ManyToManyField(
                blank=True,
                related_name="survey_templates",
                through="surveys.SurveyTemplateQuestion",
                to="surveys.question",
            ),
        ),
        migrations.AddConstraint(
            model_name="surveytemplatequestion",
            constraint=models.UniqueConstraint(
                fields=("template", "question"), name="uq_template_question"
            ),
        ),
        migrations.AddConstraint(
            model_name="surveytemplatequestion",
            constraint=models.UniqueConstraint(
                fields=("template", "position"), name="uq_template_position"
            ),
        ),
        migrations.AddConstraint(
            model_name="surveytemplatequestion",
            constraint=models.CheckConstraint(
                check=models.Q(position__gte=1) & models.Q(position__lte=8),
                name="ck_template_question_position_1_8",
            ),
        ),
    ]

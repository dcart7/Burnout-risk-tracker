from rest_framework import serializers
from django.db import transaction
from django.db.models import Max

from .models import (
    Question,
    SurveyTemplate,
    SurveyTemplateQuestion,
    SurveySubmission,
    SurveyAnswer,
)


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ("id", "text", "category", "is_active")


class SurveyTemplateQuestionWriteSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    position = serializers.IntegerField(min_value=1, max_value=8)


class SurveyTemplateQuestionReadSerializer(serializers.ModelSerializer):
    question_id = serializers.IntegerField(source="question.id", read_only=True)
    question_text = serializers.CharField(source="question.text", read_only=True)
    category = serializers.CharField(source="question.category", read_only=True)

    class Meta:
        model = SurveyTemplateQuestion
        fields = ("question_id", "question_text", "category", "position")


class SurveyTemplateSerializer(serializers.ModelSerializer):
    template_questions = SurveyTemplateQuestionWriteSerializer(
        many=True, write_only=True, required=False
    )
    questions = SurveyTemplateQuestionReadSerializer(
        source="template_questions", many=True, read_only=True
    )

    class Meta:
        model = SurveyTemplate
        fields = ("id", "version", "created_at", "is_active", "template_questions", "questions")
        read_only_fields = ("version", "created_at")

    def validate(self, attrs):
        for category in Question.Category.values:
            active_count = Question.objects.filter(category=category, is_active=True).count()
            if active_count < 25:
                raise serializers.ValidationError(
                    {
                        "template_questions": (
                            f"Not enough active questions in '{category}'. "
                            "At least 25 per category are required."
                        )
                    }
                )

        if self.instance is None and "template_questions" not in attrs:
            raise serializers.ValidationError(
                {"template_questions": "This field is required when creating a template."}
            )
        return attrs

    def validate_template_questions(self, value):
        if len(value) != 8:
            raise serializers.ValidationError("Template must contain exactly 8 questions.")

        positions = [item["position"] for item in value]
        if len(set(positions)) != 8:
            raise serializers.ValidationError("Positions must be unique from 1 to 8.")

        question_ids = [item["question_id"] for item in value]
        if len(set(question_ids)) != 8:
            raise serializers.ValidationError("Each selected question must be unique.")

        questions = Question.objects.filter(id__in=question_ids, is_active=True)
        if questions.count() != 8:
            raise serializers.ValidationError("All selected questions must exist and be active.")

        question_by_id = {question.id: question for question in questions}
        category_counts = {
            Question.Category.STRESS: 0,
            Question.Category.WORKLOAD: 0,
            Question.Category.MOTIVATION: 0,
            Question.Category.ENERGY: 0,
        }
        for item in value:
            category = question_by_id[item["question_id"]].category
            category_counts[category] += 1

        if any(count != 2 for count in category_counts.values()):
            raise serializers.ValidationError(
                "Template must contain exactly 2 questions per category."
            )

        return value

    @transaction.atomic
    def create(self, validated_data):
        template_questions = validated_data.pop("template_questions")
        next_version = (SurveyTemplate.objects.aggregate(max_version=Max("version"))["max_version"] or 0) + 1
        validated_data["version"] = next_version
        template = SurveyTemplate.objects.create(**validated_data)
        SurveyTemplateQuestion.objects.bulk_create(
            [
                SurveyTemplateQuestion(
                    template=template,
                    question_id=item["question_id"],
                    position=item["position"],
                )
                for item in template_questions
            ]
        )
        if template.is_active:
            SurveyTemplate.objects.filter(is_active=True).exclude(pk=template.pk).update(
                is_active=False
            )
        template.full_clean()
        template.save()
        return template

    @transaction.atomic
    def update(self, instance, validated_data):
        template_questions = validated_data.pop("template_questions", None)
        if template_questions is None:
            template_questions = list(
                instance.template_questions.values("question_id", "position")
            )

        next_version = (SurveyTemplate.objects.aggregate(max_version=Max("version"))["max_version"] or 0) + 1
        new_template = SurveyTemplate.objects.create(
            version=next_version,
            is_active=validated_data.get("is_active", instance.is_active),
        )
        SurveyTemplateQuestion.objects.bulk_create(
            [
                SurveyTemplateQuestion(
                    template=new_template,
                    question_id=item["question_id"],
                    position=item["position"],
                )
                for item in template_questions
            ]
        )
        if new_template.is_active:
            SurveyTemplate.objects.filter(is_active=True).exclude(pk=new_template.pk).update(
                is_active=False
            )
        new_template.full_clean()
        new_template.save()
        return new_template


class SurveyAnswerInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    score = serializers.IntegerField(min_value=0, max_value=10)


class WeeklySurveySubmissionSerializer(serializers.Serializer):
    answers = SurveyAnswerInputSerializer(many=True)

    def validate(self, attrs):
        active_templates = SurveyTemplate.objects.filter(is_active=True)
        active_templates_count = active_templates.count()
        if active_templates_count == 0:
            raise serializers.ValidationError("No active survey template is configured.")
        if active_templates_count > 1:
            raise serializers.ValidationError(
                "Multiple active survey templates found. Keep only one active template."
            )
        active_template = active_templates.prefetch_related("template_questions__question").get()

        answers = attrs["answers"]
        if len(answers) != 8:
            raise serializers.ValidationError(
                {"answers": "Weekly survey must contain exactly 8 answers."}
            )

        question_ids = [answer["question_id"] for answer in answers]
        if len(set(question_ids)) != 8:
            raise serializers.ValidationError(
                {"answers": "Each question in weekly survey must be answered only once."}
            )

        template_questions = list(active_template.template_questions.select_related("question"))
        template_question_ids = {template_question.question_id for template_question in template_questions}
        if set(question_ids) != template_question_ids:
            raise serializers.ValidationError(
                {"answers": "Answers must match exactly the 8 questions from active template."}
            )

        question_by_id = {template_question.question_id: template_question.question for template_question in template_questions}
        category_counts = {
            Question.Category.STRESS: 0,
            Question.Category.WORKLOAD: 0,
            Question.Category.MOTIVATION: 0,
            Question.Category.ENERGY: 0,
        }
        for answer in answers:
            category = question_by_id[answer["question_id"]].category
            category_counts[category] += 1

        invalid_categories = [
            category for category, count in category_counts.items() if count != 2
        ]
        if invalid_categories:
            raise serializers.ValidationError(
                {"answers": "Weekly survey must contain 2 answered questions per category."}
            )

        attrs["active_template"] = active_template
        attrs["question_by_id"] = question_by_id
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        active_template = validated_data["active_template"]
        answers_data = validated_data["answers"]
        question_by_id = validated_data["question_by_id"]

        submission = SurveySubmission.objects.create(user=user, template=active_template)
        SurveyAnswer.objects.bulk_create(
            [
                SurveyAnswer(
                    submission=submission,
                    question=question_by_id[answer["question_id"]],
                    score=answer["score"],
                )
                for answer in answers_data
            ]
        )
        return submission

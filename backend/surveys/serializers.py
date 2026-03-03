from rest_framework import serializers
from django.db import transaction

from .models import Question, SurveyTemplate, SurveyTemplateQuestion


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
        read_only_fields = ("created_at",)

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
        template.full_clean()
        template.save()
        return template

    @transaction.atomic
    def update(self, instance, validated_data):
        template_questions = validated_data.pop("template_questions", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()

        if template_questions is not None:
            instance.template_questions.all().delete()
            SurveyTemplateQuestion.objects.bulk_create(
                [
                    SurveyTemplateQuestion(
                        template=instance,
                        question_id=item["question_id"],
                        position=item["position"],
                    )
                    for item in template_questions
                ]
            )
            instance.full_clean()
            instance.save()
        return instance

from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Question, SurveyTemplate, SurveyAnswer
from .permissions import IsHRTemplateManager
from .serializers import (
    QuestionSerializer,
    SurveyTemplateSerializer,
    WeeklySurveySubmissionSerializer,
)
from users.permissions import HasRBACPermissions


class QuestionViewSet(ReadOnlyModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Question.objects.all().order_by("id")
        if self.action == "pool":
            queryset = queryset.filter(is_active=True)
            category = self.request.query_params.get("category")
            if category:
                queryset = queryset.filter(category=category)
        return queryset

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    @action(detail=False, methods=["get"], url_path="pool")
    def pool(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serialized_questions = self.get_serializer(queryset, many=True).data
        by_category = {category: [] for category in Question.Category.values}

        for question in serialized_questions:
            by_category[question["category"]].append(question)

        return Response(
            {
                "count": len(serialized_questions),
                "results": serialized_questions,
                "by_category": by_category,
            }
        )


class SurveyTemplateViewSet(ModelViewSet):
    queryset = SurveyTemplate.objects.all().order_by("-version")
    serializer_class = SurveyTemplateSerializer
    permission_classes = [IsHRTemplateManager]


class WeeklySurveySubmissionView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermissions]
    required_permissions = ("users.answer_weekly_survey",)

    def post(self, request):
        serializer = WeeklySurveySubmissionSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()
        answers = SurveyAnswer.objects.filter(submission=submission).select_related("question")

        return Response(
            {
                "submission_id": submission.id,
                "template_id": submission.template_id,
                "week_number": submission.week_number,
                "submitted_at": submission.submitted_at,
                "answers": [
                    {
                        "question_id": answer.question_id,
                        "category": answer.question.category,
                        "score": answer.score,
                    }
                    for answer in answers
                ],
            },
            status=status.HTTP_201_CREATED,
        )
